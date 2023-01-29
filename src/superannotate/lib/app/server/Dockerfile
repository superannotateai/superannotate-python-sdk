FROM tiangolo/uwsgi-nginx:python3.8


# Install requirements
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Add the app
COPY . /app
WORKDIR /app

# Make /app/* available to be imported by Python globally to better support several use cases like Alembic migrations.
ENV PYTHONPATH=/app

# Move the base entrypoint to reuse it
RUN mv /entrypoint.sh /uwsgi-nginx-entrypoint.sh

# Copy the entrypoint that will generate Nginx additional configs
COPY deployment/entrypoint.sh /entrypoint.sh
COPY deployment/uwsgi.ini /uwsgi.ini
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# Run the start script provided by the parent image tiangolo/uwsgi-nginx.
# It will check for an /app/prestart.sh script (e.g. for migrations)
# And then will start Supervisor, which in turn will start Nginx and uWSGI
CMD ["/start.sh"]
