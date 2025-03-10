from flask import Flask, request, jsonify, send_file
import os.path
from apscheduler.schedulers.background import BackgroundScheduler
import sys
from PicsDLCataba import GenerateIcons
from CosmeticsMaker import GenerateCosmetics
import threading
import requests
import time

app = Flask(__name__, static_url_path='')

def keepalive():
	print("Keeping me alive..")
	with requests.session() as s:
		s.get("https://loukios-api-906r.onrender.com/")


th = threading.Thread(target=GenerateIcons)
th.start()
tc = threading.Thread(target=GenerateCosmetics)
tc.start()

ka = threading.Thread(target=keepalive)
ka.start()



scheduler = BackgroundScheduler()
scheduler.add_job(GenerateIcons, 'cron', minute=0, second=50)
scheduler.add_job(GenerateCosmetics, 'cron', minute=0, second=50)
scheduler.add_job(keepalive, 'cron', minute=0, second=50)
scheduler.start()


def log(message):
	print(message)
	sys.stdout.flush()




@app.route('/api/v1/icons/<path:icon>', methods=['GET'])
def icons(icon):
	if icon.endswith(".png"):
		if os.path.exists("icons/{}".format(icon)):
			return send_file("icons/{}".format(icon), mimetype='image/png')
		else:
			return send_file("ph.png", mimetype='image/png')
			
	return jsonify({"status":404,"error":"the requested icon was not found"}), 404


@app.route('/api/cosmetics/br', methods=['GET'])
def cosmetics():
	if os.path.exists("cosmetics.json"):
		return send_file("cosmetics.json", mimetype='application/json')
	return jsonify({"status":404,"error":"the requested file was not found"}), 404



if __name__ == "__main__":
	app.run(debug = False , port = 80)