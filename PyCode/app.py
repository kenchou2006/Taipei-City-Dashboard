from flask import Flask, render_template, request, redirect, url_for ,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy import func
import os
from datetime import datetime
import json
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DB_MANAGER_USER')}:{os.getenv('DB_MANAGER_PASSWORD')}@{os.getenv('DB_MANAGER_HOST')}:{os.getenv('DB_MANAGER_PORT')}/{os.getenv('DB_MANAGER_DBNAME')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# 定義資料庫模型
class Component(db.Model):
    __tablename__ = 'components'

    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    history_config = db.Column(db.String)  # Assuming JSON or String type
    map_config_ids = db.Column(db.ARRAY(db.Integer))  # Assuming PostgreSQL ARRAY of Integer
    map_config = db.Column(db.String)  # Assuming JSON or String type
    chart_config = db.Column(db.String)  # Assuming JSON or String type
    map_filter = db.Column(db.String)  # Assuming JSON or String type
    time_from = db.Column(db.String)
    time_to = db.Column(db.String)
    update_freq = db.Column(db.Integer)
    update_freq_unit = db.Column(db.String)
    source = db.Column(db.String)
    short_desc = db.Column(db.Text)
    long_desc = db.Column(db.Text)
    use_case = db.Column(db.Text)
    links = db.Column(db.ARRAY(db.String))  # Assuming PostgreSQL ARRAY of String
    contributors = db.Column(db.ARRAY(db.String))  # Assuming PostgreSQL ARRAY of String
    created_at = db.Column(db.TIMESTAMP, server_default=func.now())
    updated_at = db.Column(db.TIMESTAMP, server_default=func.now(), onupdate=func.now())
    query_type = db.Column(db.String)
    query_chart = db.Column(db.Text)  # Change this to TEXT type
    query_history = db.Column(db.Text)

@app.route('/')
def show_components():
    components = Component.query.all()
    return render_template('components.html', components=components)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_component(id):
    component = Component.query.get_or_404(id)
    if request.method == 'POST':
        component.name = request.form['name']
        component.history_config = request.form['history_config'] or None
        component.map_config_ids = [int(i) for i in request.form.get('map_config_ids', '').split(',') if i.isdigit()] or None
        component.map_config = request.form['map_config'] or None
        component.chart_config = request.form['chart_config'] or None
        component.map_filter = request.form['map_filter'] or None
        component.time_from = request.form['time_from'] or None
        component.time_to = request.form['time_to'] or None
        component.update_freq = request.form['update_freq'] or None
        component.update_freq_unit = request.form['update_freq_unit'] or None
        component.short_desc = request.form['short_desc'] or None
        component.long_desc = request.form['long_desc'] or None
        component.use_case = request.form['use_case'] or None
        component.links = request.form.get('links', '').split(',') or None
        component.contributors = request.form.get('contributors', '').split(',') or None
        component.query_chart = request.form['query_chart'] or None
        component.query_history = request.form['query_history'] or None
        db.session.commit()
        return redirect(url_for('show_components'))
    return render_template('edit_component.html', component=component)

@app.route('/add', methods=['POST'])
def add_component():
    if request.method == 'POST':
        data = {
            'index': request.form['index'],
            'name': request.form['name'],
            'history_config': request.form.get('history_config', ''),
            'map_config_ids': [int(id) for id in request.form.getlist('map_config_ids[]')],
            'map_config': request.form.get('map_config', ''),
            'chart_config': request.form.get('chart_config', ''),
            'map_filter': request.form.get('map_filter', ''),
            'time_from': request.form.get('time_from', ''),
            'time_to': request.form.get('time_to', ''),
            'update_freq': int(request.form.get('update_freq', 0)),
            'update_freq_unit': request.form.get('update_freq_unit', ''),
            'source': request.form.get('source', ''),
            'short_desc': request.form.get('short_desc', ''),
            'long_desc': request.form.get('long_desc', ''),
            'use_case': request.form.get('use_case', ''),
            'links': request.form.getlist('links[]'),
            'contributors': request.form.getlist('contributors[]'),
            'created_at': request.form.get('2023-12-20 05:56:00+00'),
            'query_type': request.form.get('query_type', ''),
            'query_chart': request.form.get('query_chart', ''),
            'query_history': request.form.get('query_history', '')
        }

        new_component = Component(**data)
        db.session.add(new_component)
        db.session.commit()

        return jsonify({'message': 'Component added successfully'}), 200

if __name__ == '__main__':
    app.run(debug=True)