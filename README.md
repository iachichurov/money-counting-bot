/nash_ohuennyi_bot/
|-- bot/                          # Folder with the bot's code
|   |-- __init__.py               # So that Python understands that this is a package, not just a folder
|   |-- handlers.py               # All handlers (commands, messages, buttons) will go HERE
|   |-- keyboards.py              # We put everything related to button creation HERE
|   |-- logic.py                  # We put all the "business logic", the bot's brains, HERE
|   |-- db.py                     # We hide all the work with the database HERE
|
|-- .env                          # File with secrets. Token, database passwords. DO NOT PUSH TO GIT!
|-- .gitignore                    # List of files that Git should ignore
|-- Dockerfile                    # Dockerfile for the main application
|-- Dockerfile.cron               # Dockerfile for the cron job
|-- docker-compose.yml            # Docker-compose file for running the application
|-- crontab                       # Crontab file for scheduling jobs
|-- main.py                       # The main file. The starting switch of the whole setup.
|-- recalc_job.py                 # The script for the recalculation job.
|-- requirements.txt              # List of all libraries so that everything starts up on another machine