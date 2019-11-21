import os
from flask import Flask, render_template
from dotenv import load_dotenv

# get environment variables
load_dotenv()

app = Flask(__name__)


@app.route('/')
def index():
    return 'test'
    # return render_template("index.html")


if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=os.environ.get('DEBUG'))
