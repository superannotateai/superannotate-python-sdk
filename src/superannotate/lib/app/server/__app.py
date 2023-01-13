from superannotate import create_app
from superannotate import SAClient

sa_client = SAClient()
app = create_app([])


@app.route("/", methods=["GET"])
def health_check(request):
    return "Hello World!!!"


@app.route("/project_created", methods=["POST"])
def index(request):
    """
    Create default folders when project created.
    """
    project_name = request.json["after"]["name"]
    sa_client.create_folder(project_name, "default_folder_1")
    sa_client.create_folder(project_name, "default_folder_2")
    return "Default folders created."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
