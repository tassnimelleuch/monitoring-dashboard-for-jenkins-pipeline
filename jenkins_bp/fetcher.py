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

def get_stages(build_number):
    """Get stage breakdown for a specific build (requires Pipeline Stage View plugin)."""
    try:
        resp = requests.get(
            f'{_get_base()}/{build_number}/wfapi/describe',
            auth=_get_auth(),
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                'name':       s.get('name'),
                'status':     s.get('status'),
                'duration_ms': s.get('durationMillis', 0),
                'start_time': s.get('startTimeMillis', 0),
            }
            for s in data.get('stages', [])
        ]
    except Exception as e:
        logger.error(f'[Jenkins] get_stages error: {e}')
        return []


def get_test_report(build_number):
    """Get test results for a specific build."""
    try:
        resp = requests.get(
            f'{_get_base()}/{build_number}/testReport/api/json'
            '?tree=total,passCount,failCount,skipCount,suites[cases[name,status,duration]]',
            auth=_get_auth(),
            timeout=10
        )
        if resp.status_code == 404:
            return None  # no tests for this build
        resp.raise_for_status()
        data = resp.json()
        return {
            'total':      data.get('total', 0),
            'passed':     data.get('passCount', 0),
            'failed':     data.get('failCount', 0),
            'skipped':    data.get('skipCount', 0),
            'suites':     data.get('suites', []),
        }
    except Exception as e:
        logger.error(f'[Jenkins] get_test_report error: {e}')
        return None


def get_coverage(build_number):
    """Get code coverage for a specific build (requires Coverage plugin)."""
    try:
        resp = requests.get(
            f'{_get_base()}/{build_number}/coverage/api/json'
            '?tree=results[elements[name,ratio]]',
            auth=_get_auth(),
            timeout=10
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        elements = data.get('results', {}).get('elements', [])
        out = {}
        for el in elements:
            out[el['name'].lower()] = round(el.get('ratio', 0) * 100, 1)
        return out  # e.g. {'line': 87.3, 'branch': 72.1, 'method': 91.0}
    except Exception as e:
        logger.error(f'[Jenkins] get_coverage error: {e}')
        return None

def get_test_coverage(jenkins_url, job_name, build_number, auth):
    """Fetch coverage from JaCoCo or Cobertura plugin on last successful build."""
    # Try JaCoCo first
    for endpoint in [
        f"{jenkins_url}/job/{job_name}/{build_number}/jacoco/api/json",
        f"{jenkins_url}/job/{job_name}/{build_number}/cobertura/api/json?depth=2",
    ]:
        try:
            resp = requests.get(endpoint, auth=auth, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                # JaCoCo returns lineCoverage as a float 0.0–1.0
                if 'lineCoverage' in data:
                    return round(data['lineCoverage'] * 100, 1)
                # Cobertura returns elements with ratio
                if 'results' in data:
                    for el in data['results'].get('elements', []):
                        if el.get('name') == 'Lines':
                            return round(el['ratio'] * 100, 1)
        except Exception:
            continue
    return None

def get_pipeline_kpis():
    all_builds = get_all_builds()
    if all_builds is None:
        return {'connected': False}

    # Build comprehensive data (limit to last 50 for performance)
    builds_data = []
    for b in all_builds[:50]:
        num = b.get('number')
        stages = get_stages(num) if num else []
        tests = get_test_report(num) if num else None
        coverage = get_coverage(num) if num else None
        builds_data.append({
            'number':    num,
            'result':    b.get('result'),
            'duration':  b.get('duration', 0) // 1000 if b.get('duration') else 0,  # convert to seconds
            'timestamp': b.get('timestamp', 0),
            'stages':    stages,
            'tests':     tests,
            'coverage':  coverage,
        })

    finished = [b for b in builds_data if b['result'] is not None]
    
    # Calculate average duration (in seconds)
    durations = [b['duration'] for b in finished if b['duration'] > 0]
    avg_duration = round(sum(durations) / len(durations)) if durations else 0
    
    # Calculate failure rate by stage
    stage_failures = {}
    stage_totals = {}
    for b in finished:
        for stage in b.get('stages', []):
            stage_name = stage.get('name', 'Unknown')
            stage_totals[stage_name] = stage_totals.get(stage_name, 0) + 1
            if stage.get('status') == 'FAILED':
                stage_failures[stage_name] = stage_failures.get(stage_name, 0) + 1
    
    failure_rate_by_stage = {}
    for stage_name, count in stage_totals.items():
        failures = stage_failures.get(stage_name, 0)
        failure_rate_by_stage[stage_name] = round((failures / count * 100), 1) if count > 0 else 0
    
    # Calculate average test coverage
    coverages = []
    for b in finished:
        if b.get('coverage') and isinstance(b['coverage'], dict):
            if 'line' in b['coverage']:
                coverages.append(b['coverage']['line'])
    
    avg_coverage = round(sum(coverages) / len(coverages), 1) if coverages else 0
    
    return {
        'connected':              True,
        'builds':                 builds_data,
        'health_score':           get_health_score(),
        'avg_duration_seconds':   avg_duration,
        'failure_rate_by_stage':  failure_rate_by_stage,
        'avg_test_coverage':      avg_coverage,
        'build_durations':        [(b['number'], b['duration']) for b in finished[-20:]],  # Last 20 for chart
    }

def get_running_stages():
    """Only fetch stages for currently running builds — fast and lightweight."""
    running = get_running_builds()
    if not running:
        return []
    result = []
    for b in running:
        num    = b.get('number')
        stages = get_stages(num)
        result.append({
            'number':    num,
            'timestamp': b.get('timestamp', 0),
            'stages':    stages,
        })
    return result
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