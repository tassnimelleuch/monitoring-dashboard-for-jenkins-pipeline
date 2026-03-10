import requests
from flask import current_app

def _get_auth():
    return (
        current_app.config['JENKINS_USERNAME'],
        current_app.config['JENKINS_TOKEN']
    )

def _get_base():
    url = current_app.config['JENKINS_URL'].rstrip('/')
    job = current_app.config['JENKINS_JOB']
    return f"{url}/job/{job}"

def check_connection():
    url = _get_base()
    try:
        resp = requests.get(
            f'{url}/api/json?tree=nodeName',
            auth=_get_auth(),
            timeout=5      # don't wait more than 5 seconds
        )
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

def get_all_builds():
    url = _get_base()
    try:
        resp = requests.get(
            f'{url}/api/json?tree=builds[number,status,timestamp,duration,result]',
            auth=_get_auth(),
            timeout=10
        )
        resp.raise_for_status()
        return resp.json().get('builds', [])
    except Exception as e:
        print(f"Error fetching builds: {e}")
        return []

def get_health_score():
    """
    Jenkins calculates a health score (0-100) based on recent build results.
    It's exposed in the job's healthReport array.
    We take the first (most relevant) score.
    """
    url = _get_base()
    try:
        resp = requests.get(
            f'{url}/api/json?tree=healthReport[score,description]',
            auth=_get_auth(),
            timeout=10
        )
        resp.raise_for_status()
        reports = resp.json().get('healthReport', [])
        if reports:
            return reports[0].get('score', 0)
        return 0
    except Exception as e:
        print(f'[Jenkins] get_health_score error: {e}')
        return 0


def get_last_n_builds(n):
    """
    Get the last n builds with their metadata for trend visualization.
    """
    builds = get_all_builds()
    return builds[:n]


def get_kpis():
    """
    Main function — returns all KPIs in one dictionary.
    Called by the dashboard route to get everything at once.

    Returns:
    {
        'connected':        True/False,
        'total_builds':     int,
        'successful':       int,
        'failed':           int,
        'running':          int,
        'success_rate':     float (0-100),
        'health_score':     int (0-100),
        'build_trend':      list of last 10 builds (for charts),
    }
    """
    if not check_connection():
        return {'connected': False}

    builds     = get_all_builds()
    trend      = get_last_n_builds(10)
    health     = get_health_score()

    # Count results
    # result=None means the build is currently running
    total      = len(builds)
    running    = sum(1 for b in builds if b.get('result') is None)
    successful = sum(1 for b in builds if b.get('result') == 'SUCCESS')
    failed     = sum(1 for b in builds if b.get('result') == 'FAILURE')
    aborted    = sum(1 for b in builds if b.get('result') == 'ABORTED')

    # Success rate = successful / finished builds (exclude running)
    finished   = successful + failed + aborted
    rate       = round((successful / finished * 100), 1) if finished > 0 else 0

    return {
        'connected':    True,
        'total_builds': total,
        'successful':   successful,
        'failed':       failed,
        'aborted':      aborted,
        'running':      running,
        'success_rate': rate,
        'health_score': health,
        'build_trend':  trend,   # list of dicts with number, result, duration, timestamp
    }
    
