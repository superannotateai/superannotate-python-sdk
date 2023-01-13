import json

from lib.app.server import SAServer
from lib.core import LOG_FILE_LOCATION

app = SAServer()

LOG_FILE = "/var/log/orchestra/consumer.log"


@app.route("/monitor", methods=["GET"])
def monitor_view(request):
    return app.render_template("monitor.html", **{})


@app.route("/logs", methods=["GET"])
def logs(request):
    offset = request.args.get("offset", None)
    if offset:
        offset = int(offset)
    limit = int(request.args.get("limit", 20))
    response = {"data": []}

    with open(f"{LOG_FILE_LOCATION}/sa_server.log") as log_file:
        log_file.seek(0, 2)
        if not offset:
            offset = log_file.tell()
        cursor = max(offset - 2048, 0)
        while True:
            log_file.seek(cursor, 0)
            tmp_cursor = cursor
            for line in log_file:
                tmp_cursor += len(line)
                if tmp_cursor > offset:
                    cursor = max(cursor - 2048, 0)
                    break
                try:
                    response["data"].append(json.loads(line))
                except Exception as _:
                    ...
            cursor = max(cursor - 2048, 0)
            if len(response["data"]) >= limit or cursor == 0:
                break
            response["data"] = []
    response["offset"] = cursor
    response["data"].reverse()
    return response


#
# @app.route("/_log_stream", methods=["GET"])
# def log_stream(request):
#     def generate():
#         for line in Pygtail(LOG_FILE, every_n=1):
#             yield "data:" + str(line) + "\n\n"
#             time.sleep(0.5)
#
#     return Response(generate(), mimetype="text/event-stream")
