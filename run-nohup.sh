set -x
export FLASK_APP=application.py
export FLASK_RUN_PORT=5000
export ENV=DEV
export POSTGRES_USER=zmartboard
export POSTGRES_PASSWORD=zmartboard
#export POSTGRES_HOST=localhost
export POSTGRES_HOST=aa174s9388pu9yu.clulrco1s8ry.us-east-2.rds.amazonaws.com
export POSTGRES_PORT=5432
export POSTGRES_DB=ebdb
export APP_SETTINGS="config.DevelopmentConfig"
export DIR=/home/zmart/prod
cd $DIR
nohup flask run --host=0.0.0.0 --port=$FLASK_RUN_PORT  >log 2>&1 &

