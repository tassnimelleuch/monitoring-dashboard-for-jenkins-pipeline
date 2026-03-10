from flask import Blueprint
jenkins_bp = Blueprint('jenkins', __name__, url_prefix='/jenkins')
from jenkins_bp import routes  # noqa