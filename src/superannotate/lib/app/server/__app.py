from superannotate import SAServer

app = SAServer()


@app.route("/", methods=["POST"])
def index(request):
    return "Hello, World!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
