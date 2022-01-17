import slack
import os
from pathlib import Path
from dotenv import load_env

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])

## another git commit test