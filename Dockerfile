FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY buildexchange/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY buildexchange/ ./

# The demo database is a SQLite file created while the image is built, so the server can start straight away.
RUN python manage.py collectstatic --no-input \
 && python manage.py migrate --no-input \
 && python manage.py seed_demo \
 && python manage.py seed_marketplace

CMD ["bash", "start.sh"]
