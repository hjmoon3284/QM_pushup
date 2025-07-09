from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__, static_folder='static', static_url_path='/static')

DATA_FILE = 'pushup_records.json'
TEAM_MEMBERS = ['병선', '유경', '선주', '효성', '현정', '재욱']


def load_records():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        except:
            return []
    else:
        return []


def save_records(records):
    with open(DATA_FILE, 'w', encoding='utf-8') as file:
        json.dump(records, file, ensure_ascii=False, indent=2)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/records')
def records():
    return render_template('records.html')


@app.route('/charts')
def charts():
    return render_template('charts.html')


@app.route('/growth')
def growth():
    return render_template('growth.html')


@app.route('/save_record', methods=['POST'])
def save_record():
    try:
        data = request.get_json()

        if not data or 'date' not in data or 'time' not in data or 'members' not in data:
            return jsonify({
                'success': False,
                'message': '필수 데이터가 누락되었습니다.'
            }), 400

        records = load_records()

        new_record = {
            'id': len(records) + 1,
            'date': data['date'],
            'time': data['time'],
            'members': data['members'],
            'guests': data.get('guests', []),
            'created_at': datetime.now().isoformat()
        }

        records.append(new_record)
        save_records(records)

        return jsonify({
            'success': True,
            'message': '기록이 성공적으로 저장되었습니다!',
            'record_id': new_record['id']
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'저장 중 오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/get_records')
def get_records():
    try:
        records = load_records()
        return jsonify({
            'success': True,
            'records': records,
            'total_count': len(records)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'기록 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/delete_record/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    try:
        records = load_records()

        record_to_delete = None
        for record in records:
            if record['id'] == record_id:
                record_to_delete = record
                break

        if not record_to_delete:
            return jsonify({
                'success': False,
                'message': '삭제할 기록을 찾을 수 없습니다.'
            }), 404

        records = [record for record in records if record['id'] != record_id]
        save_records(records)

        return jsonify({
            'success': True,
            'message': f'{record_to_delete["date"]} 기록이 성공적으로 삭제되었습니다.',
            'deleted_record': record_to_delete
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'삭제 중 오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/get_stats')
def get_stats():
    try:
        records = load_records()

        if not records:
            return jsonify({
                'success': True,
                'stats': {
                    'total_records': 0,
                    'total_pushups': 0,
                    'max_daily': 0,
                    'member_stats': {},
                    'guest_records': []  # 게스트 기록 추가
                }
            })

        total_records = len(records)
        total_pushups = 0
        daily_totals = []
        member_stats = {member: {'total': 0, 'days': 0} for member in TEAM_MEMBERS}
        guest_stats = {'total_pushups': 0, 'total_guests': 0, 'unique_guests': set()}
        guest_records = []  # 게스트 상세 기록 저장

        for record in records:
            daily_total = 0

            # 정규 팀원 통계
            for member_data in record['members']:
                name = member_data['name']
                total_count = member_data.get('total_pushups', 0)

                total_pushups += total_count
                daily_total += total_count

                if name in member_stats:
                    member_stats[name]['total'] += total_count
                    if member_data.get('status') == 'participate':
                        member_stats[name]['days'] += 1

            # 게스트 통계 및 상세 기록
            if 'guests' in record and record['guests']:
                for guest_data in record['guests']:
                    guest_name = guest_data['name']
                    guest_total = guest_data.get('total_pushups', 0)
                    guest_standard = guest_data.get('standard_pushups', 0)
                    guest_knee = guest_data.get('knee_pushups', 0)

                    total_pushups += guest_total
                    daily_total += guest_total
                    guest_stats['total_pushups'] += guest_total
                    guest_stats['total_guests'] += 1
                    guest_stats['unique_guests'].add(guest_name)

                    # 게스트 상세 기록 추가
                    guest_records.append({
                        'name': guest_name,
                        'date': record['date'],
                        'standard_pushups': guest_standard,
                        'knee_pushups': guest_knee,
                        'total_pushups': guest_total,
                        'exercise_time': record.get('time', 10)
                    })

            daily_totals.append(daily_total)

        max_daily = max(daily_totals) if daily_totals else 0
        guest_stats['unique_guests'] = len(guest_stats['unique_guests'])

        # 게스트 기록을 최신순으로 정렬
        guest_records.sort(key=lambda x: x['date'], reverse=True)

        return jsonify({
            'success': True,
            'stats': {
                'total_records': total_records,
                'total_pushups': total_pushups,
                'max_daily': max_daily,
                'member_stats': member_stats,
                'guest_stats': guest_stats,
                'guest_records': guest_records  # 게스트 상세 기록 추가
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'통계 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/get_chart_data')
def get_chart_data():
    try:
        period = request.args.get('period', 'week')
        records = load_records()

        if not records:
            return jsonify({
                'success': True,
                'data': {
                    'dates': [],
                    'members': {},
                    'totals': []
                }
            })

        records.sort(key=lambda x: x['date'])
        grouped_data = group_records_by_period(records, period)

        return jsonify({
            'success': True,
            'data': grouped_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'차트 데이터 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500


@app.route('/get_individual_chart_data')
def get_individual_chart_data():
    try:
        member_name = request.args.get('member')
        records = load_records()

        if not records or not member_name:
            return jsonify({'success': False, 'message': '데이터가 없습니다.'})

        member_data = []

        for record in records:
            for member_record in record['members']:
                if (member_record['name'] == member_name and
                        member_record['status'] == 'participate' and
                        member_record.get('total_pushups', 0) > 0):
                    record_date = datetime.strptime(record['date'], '%Y-%m-%d')
                    weekdays = ['월', '화', '수', '목', '금', '토', '일']
                    display_date = f"{record_date.month}/{record_date.day} ({weekdays[record_date.weekday()]})"

                    member_data.append({
                        'date': record['date'],
                        'display_date': display_date,
                        'standard': member_record.get('standard_pushups', 0),
                        'knee': member_record.get('knee_pushups', 0),
                        'total': member_record.get('total_pushups', 0)
                    })

        member_data.sort(key=lambda x: x['date'])

        return jsonify({
            'success': True,
            'data': {
                'dates': [data['display_date'] for data in member_data],
                'standard': [data['standard'] for data in member_data],
                'knee': [data['knee'] for data in member_data],
                'total': [data['total'] for data in member_data]
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'오류: {str(e)}'
        }), 500


def group_records_by_period(records, period):
    from datetime import datetime, timedelta

    if period == 'week':
        return group_records_by_day(records)

    grouped = {}

    for record in records:
        record_date = datetime.strptime(record['date'], '%Y-%m-%d')

        if period == 'month':
            key = record_date.strftime('%Y-%m')
            display_date = f"{record_date.year}년 {record_date.month}월"
        elif period == 'quarter':
            quarter = (record_date.month - 1) // 3 + 1
            key = f"{record_date.year}-Q{quarter}"
            display_date = f"{record_date.year}년 {quarter}분기"
        else:
            key = str(record_date.year)
            display_date = f"{record_date.year}년"

        if key not in grouped:
            grouped[key] = {
                'display_date': display_date,
                'members': {member: {'standard': 0, 'knee': 0, 'total': 0} for member in TEAM_MEMBERS},
                'record_count': 0
            }

        grouped[key]['record_count'] += 1

        for member_record in record['members']:
            if member_record['status'] == 'participate':
                member_name = member_record['name']
                if member_name in grouped[key]['members']:
                    grouped[key]['members'][member_name]['standard'] += member_record.get('standard_pushups', 0)
                    grouped[key]['members'][member_name]['knee'] += member_record.get('knee_pushups', 0)
                    grouped[key]['members'][member_name]['total'] += member_record.get('total_pushups', 0)

    sorted_keys = sorted(grouped.keys())

    result = {
        'dates': [grouped[key]['display_date'] for key in sorted_keys],
        'members': {member: {'standard': [], 'knee': [], 'total': []} for member in TEAM_MEMBERS},
        'totals': []
    }

    for key in sorted_keys:
        period_total = 0
        for member in TEAM_MEMBERS:
            member_stats = grouped[key]['members'][member]
            result['members'][member]['standard'].append(member_stats['standard'])
            result['members'][member]['knee'].append(member_stats['knee'])
            result['members'][member]['total'].append(member_stats['total'])
            period_total += member_stats['total']

        result['totals'].append(period_total)

    return result


def group_records_by_day(records):
    from datetime import datetime

    daily_data = {}

    for record in records:
        date_key = record['date']
        record_date = datetime.strptime(date_key, '%Y-%m-%d')

        weekdays = ['월', '화', '수', '목', '금', '토', '일']
        display_date = f"{record_date.month}/{record_date.day} ({weekdays[record_date.weekday()]})"

        if date_key not in daily_data:
            daily_data[date_key] = {
                'display_date': display_date,
                'members': {member: {'standard': 0, 'knee': 0, 'total': 0} for member in TEAM_MEMBERS}
            }

        for member_record in record['members']:
            if member_record['status'] == 'participate':
                member_name = member_record['name']
                if member_name in daily_data[date_key]['members']:
                    daily_data[date_key]['members'][member_name]['standard'] = member_record.get('standard_pushups', 0)
                    daily_data[date_key]['members'][member_name]['knee'] = member_record.get('knee_pushups', 0)
                    daily_data[date_key]['members'][member_name]['total'] = member_record.get('total_pushups', 0)

    sorted_dates = sorted(daily_data.keys())

    result = {
        'dates': [daily_data[date]['display_date'] for date in sorted_dates],
        'members': {member: {'standard': [], 'knee': [], 'total': []} for member in TEAM_MEMBERS},
        'totals': []
    }

    for date_key in sorted_dates:
        day_data = daily_data[date_key]
        day_total = 0

        for member in TEAM_MEMBERS:
            member_stats = day_data['members'][member]
            result['members'][member]['standard'].append(member_stats['standard'])
            result['members'][member]['knee'].append(member_stats['knee'])
            result['members'][member]['total'].append(member_stats['total'])
            day_total += member_stats['total']

        result['totals'].append(day_total)

    return result


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)