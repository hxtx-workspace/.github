import datetime as dt
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('profile_generator', Path(__file__).resolve().parents[1] / 'scripts/update_profile.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PrivacyTests(unittest.TestCase):
    def test_private_and_unknown_visibility_are_never_queried(self):
        fixtures = [
            {'name': 'secret', 'private': True, 'visibility': 'private', 'owner': {'login': m.ORG}},
            {'name': 'unknown', 'private': False, 'owner': {'login': m.ORG}},
            {'name': '.github', 'private': False, 'visibility': 'public', 'owner': {'login': m.ORG}}]
        with patch.object(m, 'pages', return_value=iter(fixtures)) as pages, patch.object(m, 'api') as api:
            data = m.collect(dt.datetime.now(m.UTC))
            api.assert_not_called()
            pages.assert_called_once_with('orgs/hxtx-workspace/repos?type=public')
            self.assertEqual(data['repos'], [])
            self.assertEqual(sum(data['commits'].values()), 0)

    def test_public_totals_and_issue_pr_split(self):
        repo = {'name': 'tool-demo', 'private': False, 'visibility': 'public', 'owner': {'login': m.ORG}, 'stargazers_count': 3, 'forks_count': 2, 'size': 1}
        def pages(path):
            if path.startswith('orgs/'):
                return iter([repo])
            if '/issues?' in path:
                return iter([{'number': 1}, {'number': 2, 'pull_request': {}}])
            return iter([{'commit': {'committer': {'date': '2026-10-22T01:00:00Z'}}}])
        def api(path):
            return {'Python': 100} if path.endswith('/languages') else repo
        with patch.object(m, 'pages', side_effect=pages), patch.object(m, 'api', side_effect=api):
            data = m.collect(dt.datetime(2026, 10, 22, tzinfo=m.UTC))
        self.assertEqual((data['stars'], data['forks'], data['issues'], data['prs']), (3, 2, 1, 1))
        self.assertEqual(sum(data['commits'].values()), 1)

    def test_private_summary_requires_explicit_opt_in(self):
        config = {'categories': [{'id': 'ios', 'title': 'iOS 插件'}], 'projects': [
            {'repo': 'secret-a', 'name': 'HIDDEN-NAME', 'description': 'HIDDEN-DESCRIPTION', 'category': 'ios', 'access': 'private'},
            {'repo': 'ios-tweak-autoswipe', 'name': 'AutoSwipe', 'description': 'iOS 越狱插件', 'category': 'ios', 'access': 'private', 'publish_summary': True}]}
        now = dt.datetime.now(m.UTC)
        with patch.object(m, 'pages', return_value=iter([])):
            data = m.collect(now)
        output = m.render(config, data, now)
        self.assertNotIn('HIDDEN-NAME', output)
        self.assertNotIn('HIDDEN-DESCRIPTION', output)
        self.assertIn('AutoSwipe', output)
        self.assertIn('公开项目 **0**', output)

    def test_visibility_change_aborts_generation(self):
        repo = {'name': 'changed', 'private': False, 'visibility': 'public', 'owner': {'login': m.ORG}}
        with patch.object(m, 'pages', return_value=iter([repo])), patch.object(m, 'api', return_value={'private': True}):
            with self.assertRaises(ValueError):
                m.collect(dt.datetime.now(m.UTC))


if __name__ == '__main__':
    unittest.main()
