import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)


def _get_auth():
    return (
        current_app.config['JENKINS_USERNAME'],
        current_app.config['JENKINS_TOKEN']
    )


def _get_base():
    url = current_app.config['JENKINS_URL'].rstrip('/')
    job = current_app.config['JENKINS_JOB']
    return f"{url}/job/{job}"


def _get_root():
    return current_app.config['JENKINS_URL'].rstrip('/')


def _get_crumb_header():
    try:
        resp = requests.get(
            f'{_get_root()}/crumbIssuer/api/json',
            auth=_get_auth(),
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            return {data['crumbRequestField']: data['crumb']}
    except Exception as e:
        logger.warning(f'[Jenkins] Could not fetch crumb: {e}')
    return {}


def check_connection():
    try:
        resp = requests.get(
            f'{_get_base()}/api/json?tree=nodeName',
            auth=_get_auth(),
            timeout=5
        )
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def get_all_builds():
    try:
        resp = requests.get(
            f'{_get_base()}/api/json?tree=builds[number,status,timestamp,duration,result]',
            auth=_get_auth(),
            timeout=10
        )
        resp.raise_for_status()
        return resp.json().get('builds', [])
    except Exception as e:
        logger.error(f'[Jenkins] get_all_builds error: {e}')
        return None


def get_last_n_finished(n=10, builds=None):
    if builds is None:
        builds = get_all_builds()
    if not builds:
        return []
    finished = [b for b in builds if b.get('result') is not None]
    return finished[:n]


def get_running_builds(builds=None):
    if builds is None:
        builds = get_all_builds()
    if not builds:
        return []
    return [b for b in builds if b.get('result') is None]


def get_health_score():
    try:
        resp = requests.get(
            f'{_get_base()}/api/json?tree=healthReport[score,description]',
            auth=_get_auth(),
            timeout=10
        )
        resp.raise_for_status()
        reports = resp.json().get('healthReport', [])
        return reports[0].get('score', 0) if reports else 0
    except Exception as e:
        logger.error(f'[Jenkins] get_health_score error: {e}')
        return 0


def get_console_log(build_number):
    try:
        resp = requests.get(
            f'{_get_base()}/{build_number}/consoleText',
            auth=_get_auth(),
            timeout=30
        )
        if resp.status_code == 200:
            return resp.text
        elif resp.status_code == 404:
            return f'[ERROR] Build #{build_number} not found.'
        else:
            return f'[ERROR] Jenkins returned {resp.status_code}'
    except requests.exceptions.ConnectionError:
        return '[ERROR] Cannot connect to Jenkins.'
    except Exception as e:
        return f'[ERROR] {str(e)}'


def trigger_build():
    try:
        resp = requests.post(
            f'{_get_base()}/build',
            auth=_get_auth(),
            headers=_get_crumb_header(),
            timeout=10
        )
        if resp.status_code in (200, 201):
            return True, 'Build queued successfully'
        else:
            return False, f'Jenkins returned {resp.status_code}'
    except requests.exceptions.ConnectionError:
        return False, 'Cannot connect to Jenkins'
    except Exception as e:
        return False, str(e)


def abort_build(build_number):
    try:
        resp = requests.post(
            f'{_get_base()}/{build_number}/stop',
            auth=_get_auth(),
            headers=_get_crumb_header(),
            timeout=10
        )
        if resp.status_code in (200, 201, 302):
            return True, f'Build #{build_number} aborted'
        else:
            return False, f'Jenkins returned {resp.status_code}'
    except requests.exceptions.ConnectionError:
        return False, 'Cannot connect to Jenkins'
    except Exception as e:
        return False, str(e)


def get_kpis():
    all_builds = get_all_builds()
    if all_builds is None:
        return {'connected': False}

    finished    = get_last_n_finished(10, builds=all_builds)
    running_lst = get_running_builds(builds=all_builds)
    health      = get_health_score()

    successful = sum(1 for b in finished if b.get('result') == 'SUCCESS')
    failed     = sum(1 for b in finished if b.get('result') == 'FAILURE')
    aborted    = sum(1 for b in finished if b.get('result') == 'ABORTED')

    finished_count = successful + failed + aborted
    rate = round((successful / finished_count * 100), 1) if finished_count > 0 else 0

    durations = [b.get('duration', 0) for b in finished if b.get('duration', 0) > 0]
    avg_duration_ms = int(sum(durations) / len(durations)) if durations else 60000

    trend = running_lst + finished

    return {
        'connected':       True,
        'total_builds':    len(finished),
        'successful':      successful,
        'failed':          failed,
        'aborted':         aborted,
        'running':         len(running_lst),
        'success_rate':    rate,
        'health_score':    health,
        'build_trend':     trend,
        'avg_duration_ms': avg_duration_ms,
    }


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '/home/tasnim/Monitoring-dashboard-for-jenkins-pipeline')
    from app import create_app

    app = create_app()
    with app.app_context():
        print("=== check_connection() ===")
        print(check_connection())

        print("\n=== get_all_builds() ===")
        print(get_all_builds())

        print("\n=== get_last_n_finished(10) ===")
        print(get_last_n_finished(10))

        print("\n=== get_running_builds() ===")
        print(get_running_builds())

        print("\n=== get_health_score() ===")
        print(get_health_score())

        print("\n=== get_kpis() ===")
        print(get_kpis())