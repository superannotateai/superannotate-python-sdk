SAServer Reference
==================


The SAServer provides interface to create web API and run in development or production servers.

This will create a directory by the given name in your current or provided directory:

.. code-block:: bash

   superannotatecli create-server --name <directory_name> --path <directory_path>


Usage
________________________

SuperAnnotate Python SDK allows access to the platform without web browser:

.. code-block:: python

    import random
    from superannotate import SAClient
    from superannotate import SAServer


    app = SAServer()
    sa_client = SAClient()
    QA_EMAILS = [
        'qa1@superannotate.com', 'qa2@superannotate.com',
        'qa3@superannotate.com', 'qa4@superannotate.com'
        ]


    @app.route("item_completed", methods=["POST"])
    def index(request):
        """
        Listening webhooks on items completed events form Superannotate automation
        and is randomly assigned to qa
        """
        project_id, folder_id = request.data['project_id'], request.data['folder_id']
        project = sa_client.get_project_by_id(project_id)
        folder = sa_client.get_folder_by_id(project_id=project_id, folder_id=folder_id)
        sa_client.assign_items(
            f"{project['name']}/{folder['name']}",
            items=[request.data['name']],
            user=random.choice(QA_EMAILS)
        )


    if __name__ == '__main__':
        app.run(host='0.0.0.0', port=5002)

Interface
________________________

.. automethod:: superannotate.SAServer.route
.. automethod:: superannotate.SAServer.add_url_rule
.. automethod:: superannotate.SAServer.run


uWSGI
________________________

`uWSGI`_ is a fast, compiled server suite with extensive configuration
and capabilities beyond a basic server.

*   It can be very performant due to being a compiled program.
*   It is complex to configure beyond the basic application, and has so
    many options that it can be difficult for beginners to understand.
*   It does not support Windows (but does run on WSL).
*   It requires a compiler to install in some cases.

This page outlines the basics of running uWSGI. Be sure to read its
documentation to understand what features are available.

.. _uWSGI: https://uwsgi-docs.readthedocs.io/en/latest/

uWSGI has multiple ways to install it. The most straightforward is to
install the ``pyuwsgi`` package, which provides precompiled wheels for
common platforms. However, it does not provide SSL support, which can be
provided with a reverse proxy instead.

Install ``pyuwsgi``.

.. code-block:: text

    $ pip install pyuwsgi

If you have a compiler available, you can install the ``uwsgi`` package
instead. Or install the ``pyuwsgi`` package from sdist instead of wheel.
Either method will include SSL support.

.. code-block:: text

    $ pip install uwsgi

    # or
    $ pip install --no-binary pyuwsgi pyuwsgi


Running
________________________

The most basic way to run uWSGI is to tell it to start an HTTP server
and import your application.

.. code-block:: text

    $ uwsgi --http 127.0.0.1:8000 --master -p 4 -w wsgi:app

    *** Starting uWSGI 2.0.20 (64bit) on [x] ***
    *** Operational MODE: preforking ***
    spawned uWSGI master process (pid: x)
    spawned uWSGI worker 1 (pid: x, cores: 1)
    spawned uWSGI worker 2 (pid: x, cores: 1)
    spawned uWSGI worker 3 (pid: x, cores: 1)
    spawned uWSGI worker 4 (pid: x, cores: 1)
    spawned uWSGI http 1 (pid: x)
