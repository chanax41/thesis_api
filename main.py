import time
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import requests

import numpy as np
from scipy.stats import pearsonr
import mysql.connector
mydb = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='thesis'
)
import hashlib
# mydb = mysql.connector.connect(
#     host='thesis2022.mysql.pythonanywhere-services.com',
#     user='thesis2022',
#     password='#@sdf1234',
#     database='thesis2022$thesis'
# )

mycur = mydb.cursor()
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, redirect, url_for, session
app = Flask(__name__)

app.secret_key = 'WEZTFXTGCUygjbhbii'

@app.route('/add_sensor', methods=['GET'])
def add_sensor():
    user_id = request.args.get('user_id')
    temp = request.args.get('temp')
    spo2 = request.args.get('spo2')
    heart_rate = request.args.get('heart_rate')

    if ((temp is None) or (heart_rate is None)):
        code = 'Add to Database NOT Completed. (Data Error)'
        return code

    # Time zone in Thailand UTC+7
    tz = timezone(timedelta(hours=7))
    # Create a date object with given timezone
    date = datetime.now(tz=tz)
    # Display time
    print(date)

    sql = 'INSERT INTO sensors (timestemp, temp, spo2, heart_rate, user_id) VALUES (%s, %s, %s, %s, %s)'
    val = (date, temp, spo2, heart_rate, user_id)
    mycur.execute(sql, val)
    mydb.commit()
    error = mycur.fetchwarnings()
    if error is None:
        code = 'Add to Database Completed.'
    else:
        code = 'Add to Database NOT Completed. Error: ' + error

    return code

@app.route('/show_data')
def show_data2():
    sql = 'SELECT ID, fname, lname, email, address FROM user_web WHERE status="ACTIVE" and position="patient" order by ID DESC;'
    mycur.execute(sql)
    data = mycur.fetchall()
    return render_template('showdata.html', data=data, title='Show Data')


@app.route("/")
@app.route("/check", methods=['POST'])
def index():
    msg = ""
    num_home = []
    if request.method == "POST":
        user = request.form['username']
        cpassword = hashlib.md5(request.form['password'].encode())
        password_en = cpassword.hexdigest()
        sql = 'SELECT ID FROM user_web WHERE username = %s and password = %s and status = "ACTIVE";'
        mycur.execute(sql, (user, password_en))
        count_id = mycur.fetchone()
        if count_id is not None and len(count_id) == 1:
            session['user_id'] = count_id[0]
            sql = 'SELECT lat, lng, fname, lname, address, ID FROM user_web WHERE position ="patient" and status = "ACTIVE";'
            mycur.execute(sql)
            result1 = mycur.fetchall()
            num_member = len(result1)

            sql = 'SELECT COUNT(*) FROM `user_web` WHERE status ="Death" and position="patient";'
            mycur.execute(sql)
            result = mycur.fetchone()
            num_death = result[0]

            sql = 'SELECT COUNT(*) FROM `user_web` WHERE position="patient";'
            mycur.execute(sql)
            result = mycur.fetchone()
            num_all = result[0]

            sql = 'SELECT COUNT(*) FROM `user_web` WHERE status ="Recovered" and position="patient";'
            mycur.execute(sql)
            result = mycur.fetchone()
            num_rec = result[0]

            sql = 'SELECT COUNT(*) FROM `user_web` WHERE status ="ACTIVE" and position="patient";'
            mycur.execute(sql)
            result = mycur.fetchone()
            num_act = result[0]

            num_home = [num_all, num_rec, num_act, num_death]

            return render_template('index.html', title='Home', position=result1, num_member=num_member, num_home=num_home)
        else:
            msg = "username or password is incorrect"
            session['user_id'] = None
            return render_template('login.html', title='login', msg=msg)
    else:
        # Line Notification
        def print_date_time():
            time_server = time.strftime("%A, %d. %B %Y %I:%M:%S %p")
            print(time_server)
            sql = "SELECT user_web.ID, user_web.fname, user_web.lname, user_web.lat, user_web.lng, sensors.timestemp, sensors.temp, sensors.spo2, sensors.heart_rate, sensors.user_id, emotion.emotion, emotion.user_id FROM user_web, sensors, emotion WHERE user_web.ID = sensors.user_id AND user_web.ID = emotion.user_id ORDER BY sensors.timestemp DESC LIMIT 1;"
            mycur.execute(sql)
            result_noti = mycur.fetchone()
            print(result_noti)

            if ((result_noti[8] <= 25 or result_noti[10] == "Risky") and result_noti[7] <= 94 and result_noti[6] >= 39):
                url = 'https://notify-api.line.me/api/notify'
                token = 'T3CLU0xXE36eJxdBjgVgb882JRQ9eVbPsUyPMEc1cuF'
                headers = {
                    'content-type':
                        'application/x-www-form-urlencoded',
                    'Authorization': 'Bearer ' + token
                }
                msg = "System predicted that the patient.\nName-Surname: {0} {1} is a risk of requiring medical attention. \nPlease go to this position urgently: https://www.google.com/maps/search/'{2}+{3}'\n------------------------------------------------\nBPM: {4} \nSpO2: {5} \nTemp: {6}  ํC"

                r = requests.post(url, headers=headers, data={'message': msg.format(result_noti[1], result_noti[2], result_noti[3], result_noti[4], result_noti[8], result_noti[7], result_noti[6])})
                print(r.text)

        scheduler = BackgroundScheduler()
        scheduler.add_job(func=print_date_time, trigger="interval", seconds=60)
        scheduler.start()

        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())

        try:
            if session['user_id'] == None:
                return render_template('login.html', title='login', msg=msg)
            else:
                sql = 'SELECT lat, lng, fname, lname, address, ID FROM user_web WHERE position ="patient" and status = "ACTIVE";'
                mycur.execute(sql)
                result1 = mycur.fetchall()
                num_member = len(result1)

                sql = 'SELECT COUNT(*) FROM `user_web` WHERE status ="Death" and position="patient";'
                mycur.execute(sql)
                result = mycur.fetchone()
                num_death = result[0]

                sql = 'SELECT COUNT(*) FROM `user_web` WHERE position="patient";'
                mycur.execute(sql)
                result = mycur.fetchone()
                num_all = result[0]

                sql = 'SELECT COUNT(*) FROM `user_web` WHERE status ="Recovered" and position="patient";'
                mycur.execute(sql)
                result = mycur.fetchone()
                num_rec = result[0]

                sql = 'SELECT COUNT(*) FROM `user_web` WHERE status ="ACTIVE" and position="patient";'
                mycur.execute(sql)
                result = mycur.fetchone()
                num_act = result[0]

                num_home = [num_all, num_rec, num_act, num_death]

                return render_template('index.html', title='Home', position=result1, num_member=num_member, num_home=num_home)
        except:
            return render_template('login.html', title='login', msg=msg)

@app.route('/logout')
def logout():
    session['user_id'] = None
    return redirect(url_for('index'))

@app.route("/analysis")
@app.route("/analysis_chart", methods=['post'])
def analysis():
    if request.method == "POST":
        factor_x = request.form['factor_x']
        factor_y = request.form['factor_y']
        print(factor_x, factor_y)
        sql = 'SELECT * FROM sensors ORDER BY id DESC LIMIT 500;'
        mycur.execute(sql)
        result = mycur.fetchall()
        temp = []
        SpO2 = []
        HR = []
        #datetime = []
        scetterdata = ''
        for item in result:
            # date_time = item[1].strftime('%Y-%m-%d %H:%M:%S')
            # print("date and time:", date_time)
            # datetime.append(date_time)
            temp.append(item[2])
            SpO2.append(item[3])
            HR.append(item[4])

        def find_reg(fx,fy):
            reg_data = ''
            # Define the data
            x = np.array(fx)
            y = np.array(fy)

            # Fit a polynomial of degree 1 to the data using least squares regression
            m, c = np.polyfit(x, y, 1)

            # Print the slope and y-intercept
            m = round(m, 2)
            c = round(c, 2)
            reg = "y = "+str(m)+"x +"+str(c)

            for i in range(len(fx)):
                reg_data = reg_data + '{x:' + str(fx[i]) + ', y:' + str(m*fx[i] + c) + '},'
            corr, _ = pearsonr(fx, fy)
            print('Pearsons correlation: %.3f' % corr)
            print(reg)
            corr = round(corr, 2)
            corr = "Pearsons correlation: "+str(corr)
            reg_data = [reg_data, reg, corr]
            return reg_data

        if factor_x == "Temp" and factor_y == "HeartRate":
            reg_data = find_reg(temp, HR)
            print(reg_data[2])
            for i in range(len(temp)):
                scetterdata = scetterdata + '{x:'+str(temp[i])+', y:'+str(HR[i])+'},'
            return render_template('analysis.html', title='Analysis', fx=temp, fy=HR,
                                       scetter=scetterdata, ax="Temperature", ay="Heart Rate", reg_data=reg_data[0], reg=reg_data[1],cor=reg_data[2])
        elif factor_x == "HeartRate" and factor_y == "Temp":
            reg_data= find_reg(HR,temp)
            for i in range(len(HR)):
                scetterdata = scetterdata + '{x:'+str(HR[i])+', y:'+str(temp[i])+'},'
            return render_template('analysis.html', title='Analysis', fx=HR, fy=temp,
                                   scetter=scetterdata, ax="Heart Rate", ay="Temperature", reg_data=reg_data[0], reg=reg_data[1],cor=reg_data[2])
        elif factor_x == "HeartRate" and factor_y == "SpO2":
            reg_data = find_reg(HR,SpO2)
            for i in range(len(HR)):
                    scetterdata = scetterdata + '{x:'+str(HR[i])+', y:'+str(SpO2[i])+'},'
            return render_template('analysis.html', title='Analysis', fx=HR, fy=SpO2,
                                   scetter=scetterdata, ax="Heart Rate", ay="SpO2", reg_data=reg_data[0], reg=reg_data[1],cor=reg_data[2])
        elif factor_x == "SpO2" and factor_y == "HeartRate":
            reg_data = find_reg(SpO2, HR)
            for i in range(len(SpO2)):
                scetterdata = scetterdata + '{x:'+str(SpO2[i])+', y:'+str(HR[i])+'},'
            return render_template('analysis.html', title='Analysis', fx=SpO2, fy=HR,
                                    scetter=scetterdata, ax="SpO2", ay="Heart Rate", reg_data=reg_data[0], reg=reg_data[1],cor=reg_data[2])
        elif factor_x == "SpO2" and factor_y == "Temp":
            reg_data = find_reg(SpO2, temp)
            for i in range(len(SpO2)):
                scetterdata = scetterdata + '{x:'+str(SpO2[i])+', y:'+str(temp[i])+'},'
            return render_template('analysis.html', title='Analysis', fx=SpO2, fy=temp,
                                   scetter=scetterdata, ax="SpO2", ay="Temperature", reg_data=reg_data[0], reg=reg_data[1],cor=reg_data[2])
        elif factor_x == "Temp" and factor_y == "SpO2":
            reg_data = find_reg(temp, SpO2)
            for i in range(len(temp)):
                scetterdata = scetterdata + '{x:'+str(temp[i])+', y:'+str(SpO2[i])+'},'
            return render_template('analysis.html', title='Analysis', fx=temp, fy=SpO2,
                                    scetter=scetterdata, ax="Temperature", ay="SpO2", reg_data=reg_data[0], reg=reg_data[1],cor=reg_data[2])
        else:
            return render_template('analysis.html', title='Analysis')
    return render_template('analysis.html', title='Analysis')

@app.route("/manage_user")
def manage_user():
    sql = 'SELECT * FROM user_web order by ID DESC;'
    mycur.execute(sql)
    data = mycur.fetchall()
    return render_template('showuser.html', title='Manage User', data=data)

@app.route("/add_user")
def add_user():
    return render_template('adduser.html', title='Add User')

@app.route("/edit_user")
def edit_user():
    return render_template('adduser.html', title='Edit User')

@app.route("/add_user_db", methods=['POST'])
def add_user_db():
    if request.method == "POST":
        username = request.form['username']
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        address = request.form['address']
        latitude = request.form['latitude']
        longitude = request.form['longitude']
        position = request.form['position']
        password = request.form['password'].encode()
        cpassword = request.form['cpassword'].encode()
        if (password == cpassword) and position != 'null':
            cpassword = hashlib.md5(request.form['cpassword'].encode())
            password_en = cpassword.hexdigest()
            sql = 'INSERT INTO `user_web`(`username`, `password`, `status`, `fname`, `lname`, `email`, `address`, `lat`, `lng`, `position`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
            val = (username, password_en, 'ACTIVE', fname, lname, email, address, latitude, longitude, position)
            mycur.execute(sql, val)
            mydb.commit()
            return redirect(url_for('manage_user'))
        else:
            msg = 'Password does not match or Incomplete information.'
            return render_template('adduser.html', title='Add User', msg=msg)

@app.route("/user_details")
def user_details():
    session['user_id'] = 1
    # ID = request.agrs.get("ID")
    ID = 1
    sql = 'SELECT * FROM user_web WHERE ID=%s;'
    mycur.execute(sql, (ID,))
    data_user = mycur.fetchone()
    print(data_user)
    if data_user[3] == 'Recovered':
        check_re = "checked"
        check_not_re = ""
        check_de = ""
    elif data_user[3] == 'Death':
        check_re = ""
        check_not_re = ""
        check_de = "checked"
    else:
        check_re = ""
        check_not_re = "checked"
        check_de = ""

    print(bool(check_re), bool(check_not_re), bool(check_de))
    sql = """SELECT user_web.ID, sensors.timestemp, sensors.temp, sensors.spo2, sensors.heart_rate, emotion.emotion
            FROM user_web, sensors, emotion 
            WHERE user_web.ID = %s AND user_web.ID = sensors.user_id AND user_web.ID = emotion.user_id ORDER BY sensors.timestemp DESC LIMIT 50;"""
    val = (ID,)
    mycur.execute(sql, val)
    result = mycur.fetchall()
    Temp = []
    HR = []
    SpO2 =[]
    date = []
    datetime = []
    predict = []
    colors = []
    for item in result:
        level = 0
        date_time = item[1].strftime('%Y-%m-%d %H:%M:%S')
        date_time = date_time.split()
        date.append(date_time[0])
        datetime.append(date_time[1])
        Temp.append(item[2])
        SpO2.append(item[3])
        HR.append(item[4])
        predict.append(item[5])

        if item[2] >= 39:
            level += 1
        if item[3] <= 94:
            level += 1
        if item[4] <= 25:
            level += 1
        if item[5] == 'Risky':
            level += 1

        if level == 0:
            color = "#26A69A"
        elif level == 1:
            color = "#F2C94C"
        elif level == 2:
            color = "#FF5722"
        else:
            color = "#EE1D52"
        colors.append(color)


    return render_template('user_details.html', title='User Details', ID=ID, date=date, datetime=datetime,Temp=Temp,HR=HR, Hum=SpO2, predict =predict, colors=colors, data_user=data_user, check_not_re=check_not_re, check_re=check_re, check_de=check_de)

@app.route("/update_status", methods=["POST"])
def update_status():
    status = request.form['update_status']
    ID = request.form['ID']
    if status == "Recovered":
        sql = "UPDATE `user_web` SET `status` = 'Recovered' WHERE `user_web`.`ID` = %s;"
        mycur.execute(sql, (ID,))
        mydb.commit()
        return render_template("updatecom.html", ID=ID)
    elif status == "Death":
        sql = "UPDATE `user_web` SET `status` = 'Death' WHERE `user_web`.`ID` = %s;"
        mycur.execute(sql, (ID,))
        mydb.commit()
        return render_template("updatecom.html", ID=ID)

    else:
        sql = "UPDATE `user_web` SET `status` = 'ACTIVE' WHERE `user_web`.`ID` = %s;"
        mycur.execute(sql, (ID,))
        mydb.commit()
        return render_template("updatecom.html", ID=ID)




if __name__ == '__main__':
    app.run(debug=True)
