#!/usr/bin/env python3
'''
GitHub Memory - GitHub integration for Nyx using gh CLI
Uses `gh auth` for OAuth - browser click to authorize, works perfectly!
'''

import os
import subprocess
import json
from pathlib import Path
from typing import Optional

# ============================================================================
# OAUTH TOKEN STORAGE (via gh token)
# ============================================================================

def get_gh_token() -> Optional[str]:
    '''Get GitHub token via gh CLI'''
    try:
        result = subprocess.run(
            ['gh', 'auth', 'token', '--hostname', 'github.com'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            token = result.stdout.strip()
            if token:
                return token
    except:
        pass
    return None

def is_gh_authenticated() -> bool:
    '''Check if gh is authenticated'''
    try:
        result = subprocess.run(
            ['gh', 'auth', 'status'],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0 and 'Logged in to github.com' in result.stdout
    except:
        return False

def authenticate_via_gh():
    '''Authenticate with GitHub via gh CLI - just runs `gh auth login`'''
    print('\n🌐 Opening GitHub login in browser...')
    print('   (gh auth login will open your browser for OAuth)\n')
    
    try:
        result = subprocess.run(
            ['gh', 'auth', 'login', '--hostname', 'github.com', '--web'],
            timeout=120
        )
        if result.returncode == 0:
            token = get_gh_token()
            if token:
                print('\n✓ GitHub authentication successful!')
                return True
        print('\n✗ Authentication failed')
        return False
    except Exception as e:
        print(f'\n✗ Error: {e}')
        return False

def clear_github_token():
    '''Logout from gh'''
    try:
        subprocess.run(['gh', 'auth', 'logout', '--hostname', 'github.com', '--yes'],
                      capture_output=True, timeout=10)
    except:
        pass

# ============================================================================
# GITHUB API CLIENT (via gh or direct API)
# ============================================================================

class GitHubMemory:
    
    def __init__(self, supabase_client=None):
        self.github_token = get_gh_token()
        self.headers = {}
        if self.github_token:
            self.headers['Authorization'] = f'token {self.github_token}'
        self.headers['Accept'] = 'application/vnd.github.v3+json'
        self.supabase = supabase_client
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    def authenticate(self):
        '''Authenticate via gh CLI - one command!'''
        return authenticate_via_gh()
    
    def authenticate_via_browser(self, console=None):
        '''Alias for authenticate()'''
        return authenticate_via_gh()
    
    def gh_graphql(self, query: str) -> dict:
        '''Execute GraphQL query via gh api'''
        try:
            result = subprocess.run(
                ['gh', 'api', 'graphql', '-f', f'query={query}'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            return {'error': result.stderr}
        except Exception as e:
            return {'error': str(e)}
    
    def gh_api(self, endpoint: str) -> dict:
        '''Execute REST API via gh api'''
        try:
            result = subprocess.run(
                ['gh', 'api', endpoint],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            return {'error': result.stderr}
        except Exception as e:
            return {'error': str(e)}
    
    def _api_request(self, url: str, params: dict = None) -> dict:
        '''Make authenticated GitHub API request'''
        import requests
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {'error': str(e)}
    
    def get_current_user(self) -> dict:
        '''Get current GitHub user via gh'''
        data = self.gh_api('user')
        if 'error' in data:
            return {'login': 'anonymous', 'name': 'Anonymous', 'avatar_url': '', 'public_repos': 0}
        return {
            'login': data.get('login', 'anonymous'),
            'name': data.get('name', data.get('login', 'Anonymous')),
            'avatar_url': data.get('avatar_url', ''),
            'bio': data.get('bio', ''),
            'public_repos': data.get('public_repos', 0)
        }
    
    def list_repos(self, per_page: int = 30) -> list:
        '''List user's repositories via gh'''
        query = '''
 query { 
   viewer { 
     repositories(first: %d, orderBy: {field: UPDATED_AT, direction: DESC}) {
       nodes {
         name
         fullName: nameWithOwner
         description
         url
         stargazerCount
         primaryLanguage { name }
         topics: repositoryTopics(first: 5) { nodes { topic { name } } }
       }
     }
   }
 }
''' % per_page
        
        data = self.gh_graphql(query)
        try:
            repos = data['data']['viewer']['repositories']['nodes']
            return [{
                'name': r.get('name', ''),
                'full_name': r.get('fullName', ''),
                'description': r.get('description', '') or '',
                'url': r.get('url', ''),
                'stars': r.get('stargazerCount', 0),
                'language': r.get('primaryLanguage', {}).get('name', '') if r.get('primaryLanguage') else '',
                'topics': [t['topic']['name'] for t in r.get('topics', {}).get('nodes', [])],
            } for r in repos]
        except:
            return []
    
    def search_repos(self, query: str, per_page: int = 10) -> list:
        '''Search repositories via gh'''
        data = self.gh_api(f'search/repositories?q={query}&per_page={per_page}&sort=stars&order=desc')
        if 'items' in data:
            return [{
                'name': r.get('name', ''),
                'full_name': r.get('full_name', ''),
                'description': r.get('description', '') or '',
                'url': r.get('html_url', ''),
                'stars': r.get('stargazers_count', 0),
                'language': r.get('language', '') or '',
            } for r in data['items']]
        return []
    
    def get_repo_issues(self, repo: str, state: str = 'open') -> list:
        '''Get issues for a repository via gh'''
        data = self.gh_api(f'repos/{repo}/issues?state={state}&per_page=20&sort=updated')
        if isinstance(data, list):
            return [{
                'number': i.get('number', 0),
                'title': i.get('title', ''),
                'state': i.get('state', ''),
                'labels': [l.get('name', '') for l in i.get('labels', [])],
                'url': i.get('html_url', ''),
                'author': i.get('user', {}).get('login', ''),
            } for i in data if 'pull_request' not in i]
        return []
    
    def format_repos(self, repos: list) -> str:
        '''Format repository list'''
        if not repos:
            return '\nNo repositories found'
        
        lines = ['\n╔════════════════════════════════════════════════════════╗',
                 '║  📦 GitHub Repositories                                ║',
                 '╠════════════════════════════════════════════════════════╣']
        
        for repo in repos[:10]:
            stars = f'⭐ {repo["stars"]}' if repo.get('stars') else ''
            lang = f'[{repo["language"]}]' if repo.get('language') else ''
            desc = repo.get('description', '')[:50]
            lines.append(f'║  {repo["full_name"]} {stars} {lang}')
            if desc:
                lines.append(f'║    {desc}')
        
        lines.append('╚════════════════════════════════════════════════════════╝')
        return '\n'.join(lines)
    
    def get_status(self) -> str:
        '''Get GitHub connection status'''
        user = self.get_current_user()
        
        lines = ['\n╔════════════════════════════════════════════════════════╗',
                 '║  🐙 GitHub Memory Status                                ║',
                 '╠════════════════════════════════════════════════════════╣']
        
        if user.get('login') != 'anonymous':
            login = user.get('login', '')
            repos = user.get('public_repos', 0)
            lines.append(f'║  ✓ Connected as: {login}')
            lines.append(f'║    Repos: {repos}')
            lines.append('║                                                        ║')
            lines.append('║  Commands:                                             ║')
            lines.append('║    /github auth    - Re-authenticate (gh auth login)    ║')
            lines.append('║    /github repos   - List your repositories             ║')
            lines.append('║    /github issues  - Show your open issues              ║')
            lines.append('║    /github search  - Search GitHub                      ║')
        else:
            lines.append('║  ⚠ Not authenticated                                    ║')
            lines.append('║                                                        ║')
            lines.append('║    Run /github auth to login via browser!               ║')
        
        lines.append('╚════════════════════════════════════════════════════════╝')
        return '\n'.join(lines)

if __name__ == '__main__':
    gm = GitHubMemory()
    print(gm.get_status())
