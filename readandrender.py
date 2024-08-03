'''
This Flask web application reads data from a JSON file, processes it to extract IP diversity details, and renders the information on an HTML dashboard.The dashboard displays the sorted IP diversity data by date, also list all down IPs .
'''


import json
from flask_cors import CORS
from datetime import datetime
# from ip_diversity_data_scraper import logger
from flask import Flask, jsonify, render_template

app = Flask(__name__)
CORS(app)  # Enable for all routes, if needed


'''
Route to render the dashboard
'''
@app.route("/")
def render_data():
    try:
        #opening the JSON file
        with open('ip_diversity_details.json', 'r') as file: 
            data = json.load(file)
            final_list = data.get('final_list', [])
            down_ips = data.get('down_ips', [])
            last_run_time = data.get('last_run_time', '')

        #  Validate if data is empty
        if not final_list:
            # logger.warning("Empty or incomplete data found in 'ip_diversity_details.json'.")
            return "Data not found or incomplete"
        
        #extracting all dates into a set
        dates = set()
        for server_data in final_list:
            for server, details in server_data.items():
                dates.update(details.get('ipdiversity', {}).keys())
        #sorting dates in descending order (first display current date)
        sorted_dates = sorted(dates, key=lambda x: datetime.strptime(x, "%d-%m-%y"), reverse=True)
        if len(sorted_dates) > 11:
            del sorted_dates[11:]
           
        # rendering into HTML file        
        return render_template('ip_diversity_dashboard.html', data=final_list, dates=sorted_dates, down=down_ips, last_run=last_run_time)
    except FileNotFoundError:
        # logger.error("File 'ip_diversity_details.json' not found.")
        return "File not found"
    except Exception as e:
        # logger.exception("An error occurred while processing the request.")
        return f"An error occurred: {str(e)}"
    
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=80)
