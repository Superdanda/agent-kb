from flask import Flask
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello from DevOps! App version: " + __import__('os').environ.get('APP_VERSION', 'dev')

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)