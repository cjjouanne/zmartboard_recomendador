set -x
export FLASK_APP=application.py
export FLASK_RUN_PORT=5000
export ENV=DEV
export POSTGRES_USER=zmartboard
export POSTGRES_PASSWORD=zmartboard
export POSTGRES_HOST=aa1t4b71jqomzxa.clulrco1s8ry.us-east-2.rds.amazonaws.com
export POSTGRES_PORT=5432
export POSTGRES_DB=ebdb
export APP_SETTINGS="config.DevelopmentConfig"
export DIR=/home/zmart/prod
cd $DIR
source prodenv/bin/activate
#set +x
#flask run --host=0.0.0.0 --port=$FLASK_RUN_PORT
#gunicorn  --bind 0.0.0.0:$FLASK_RUN_PORT wsgi:application --timeout 300
#gunicorn --workers 3 --bind unix:sysrec.sock -m 007 wsgi:application --timeout 300 --chmod-socket=555
#gunicorn --workers 2 --bind unix:sysrec.sock  wsgi:application --timeout 180000000 >>loguni.log 2>&1 &
gunicorn --workers 1 --bind unix:sysrec.sock  wsgi:application --timeout 180000000 >>loguni.log 2>&1 &
