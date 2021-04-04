from flask import Blueprint, jsonify, request
from data import db_session, jobs

blueprint = Blueprint("jobs_api", __name__, template_folder="templates")


@blueprint.route("/api/jobs")
def get_jobs():
    session = db_session.create_session()
    jobs_ = session.query(jobs.Jobs).all()
    return jsonify(
        {
            'jobs':
                [item.to_dict(
                    only=('team_leader', 'job', 'work_size', 'collaborators', 'is_finished', 'start_date', 'end_date'))
                    for item in jobs_]
        }
    )


@blueprint.route("/api/jobs/<int:jobs_id>", methods=["GET"])
def get_one_job(jobs_id):
    session = db_session.create_session()
    job = session.query(jobs.Jobs).get(jobs_id)
    if not job:
        return jsonify({'error': 'Not found'})
    return jsonify(
        {
            'jobs':
                job.to_dict(
                    only=('team_leader', 'job', 'work_size', 'collaborators', 'is_finished', 'start_date', 'end_date'))
        }
    )


@blueprint.route("/api/jobs", methods=["POST"])
def create_job():
    if not request.json:
        return jsonify({"error": "Empty request"})
    elif not all(
            key in request.json for key in ["team_leader", "job", "work_size", "collaborators", "is_finished", "id"]):
        return jsonify({"error": "Bad request"})
    session = db_session.create_session()
    ex_job = session.query(jobs.Jobs).filter(jobs.Jobs.id == request.json["id"])
    if ex_job:
        return jsonify({"error": "Id already exists"})
    job = jobs.Jobs(
        id=request.json["id"],
        team_leader=request.json["team_leader"],
        job=request.json["job"],
        work_size=request.json["work_size"],
        collaborators=request.json["collaborators"],
        is_finished=request.json["is_finished"]
    )
    session.add(job)
    session.commit()
    return jsonify({"success": "OK"})


@blueprint.route("/api/jobs/<int:jobs_id>", methods=["DELETE"])
def delete_job(jobs_id):
    session = db_session.create_session()
    job = session.query(jobs.Jobs).get(jobs_id)
    if not job:
        return jsonify({"error": "Not found"})
    session.delete(job)
    session.commit()
    return jsonify({"success": "OK"})


@blueprint.route("/api/jobs/<int:jobs_id>", methods=["PUT"])
def edit_job(jobs_id):
    if not request.json:
        return jsonify({"error": "Empty request"})
    elif not all(
            key in request.json for key in ["team_leader", "job", "work_size", "collaborators", "is_finished"]):
        return jsonify({"error": "Bad request"})
    session = db_session.create_session()
    job = session.query(jobs.Jobs).get(jobs_id)
    if not job:
        return jsonify({"error": "Id doesn't exist"})
    job.team_leader = request.json["team_leader"]
    job.job = request.json["job"]
    job.work_size = request.json["work_size"]
    job.collaborators = request.json["collaborators"]
    job.is_finished = request.json["is_finished"]
    session.commit()
    return jsonify({"success": "OK"})
