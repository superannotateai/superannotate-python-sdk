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
    data = []
    limit = 20
    items = []
    cursor = None
    get_cursor = lambda x: max(x - 2048, 0)

    with open(
        f"{LOG_FILE_LOCATION}/sa_server.log",
    ) as log_file:
        log_file.seek(0, 2)
        file_size = log_file.tell()
        cursor = get_cursor(file_size)
        while True:
            log_file.seek(cursor, 0)
            lines = log_file.read().splitlines()[-limit:]
            # if cursor == 0 and len(lines) >= limit:
            #     continue
            for line in lines:
                try:
                    items.append(json.loads(line))
                except Exception:
                    ...
            if len(lines) >= limit or cursor == 0:
                return items
            cursor = get_cursor(cursor)
            items = []


#
# @app.route("/_log_stream", methods=["GET"])
# def log_stream(request):
#     def generate():
#         for line in Pygtail(LOG_FILE, every_n=1):
#             yield "data:" + str(line) + "\n\n"
#             time.sleep(0.5)
#
#     return Response(generate(), mimetype="text/event-stream")
