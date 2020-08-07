import requests
import re
import datetime
import configparser
import hashlib
import json
import os


def md5(str):
    m = hashlib.md5()
    m.update(str.encode("utf8"))
    return m.hexdigest()


config = configparser.ConfigParser()
config.read('config.ini')

# 教务系统地址
url = config['URP'].get('url')
username = input('id:')
password = input('password:')
session = requests.session()
im_url = url + 'img/captcha.jpg'
im_data = session.get(im_url)

# 验证码处理及模拟登陆
with open('captcha.jpg', 'wb') as file:
    file.write(im_data.content)
captcha = input("Captcha(saved in the code directory):")
login_url = url + 'j_spring_security_check'
post_data = {
    'j_username': username,
    'j_password': md5(password),
    'j_captcha': captcha
}

# 课表数据获取
login_res = session.post(login_url, data=post_data)
table_url = url + 'student/courseSelect/thisSemesterCurriculum/ajaxStudentSchedule/curr/callback'
tablePage = session.get(table_url).text
table_byte = bytes(tablePage, 'utf-8')

# 数据预处理
with open('class.json', 'wb') as file:
    file.write(table_byte)
    file.close()

with open('class.json', "a+", encoding='utf-8') as f:
    old = f.read()
    f.seek(0)
    f.write(']')
    f.close()

with open('class.json', "r+", encoding='utf-8') as f:
    old = f.read()
    f.seek(0)
    f.write('[')
    f.write(old)

# 写入日历
# 第一周周一日期
startYear = config['startDate'].getint('year')
startMonth = config['startDate'].getint('month')
startDay = config['startDate'].getint('day')

beginDate = datetime.date(startYear, startMonth, startDay)

startTime = [None]
startTime.extend(config['time'].get('startTime').replace(' ', '').split(','))

endTime = [None]
endTime.extend(config['time'].get('endTime').replace(' ', '').split(','))

weekName = [None]
weekName.extend(config['time'].get('weekName').replace(' ', '').split(','))

VCALENDAR = '''BEGIN:VCALENDAR
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:%(username)s 课程表
X-WR-TIMEZONE:Asia/Shanghai
X-WR-CALDESC:%(username)s 课程表
BEGIN:VTIMEZONE
TZID:Asia/Shanghai
X-LIC-LOCATION:Asia/Shanghai
BEGIN:STANDARD
TZOFFSETFROM:+0800
TZOFFSETTO:+0800
TZNAME:CST
DTSTART:19700101T000000
END:STANDARD
END:VTIMEZONE
''' % {'username': username}

file = open('课程表.ics', 'w', encoding='utf-8')
file.write(VCALENDAR)

with open("class.json", 'r', encoding='utf-8') as f:
    temp = json.loads(f.read())
    for index in range(len(temp[0]['dateList'][0]['selectCourseList'])):
        # 剔除未安排教室的课程
        if temp[0]['dateList'][0]['selectCourseList'][index]['timeAndPlaceList'] is None:
            continue
        for index1 in range(len(temp[0]['dateList'][0]['selectCourseList'][index]['timeAndPlaceList'])):
            className = temp[0]['dateList'][0]['selectCourseList'][index]['courseName']
            classBuilding = temp[0]['dateList'][0]['selectCourseList'][index]['timeAndPlaceList'][index1][
                'teachingBuildingName']
            classRoom = temp[0]['dateList'][0]['selectCourseList'][index]['timeAndPlaceList'][index1]['classroomName']
            classSession = temp[0]['dateList'][0]['selectCourseList'][index]['timeAndPlaceList'][index1][
                'classSessions']
            classAmount = temp[0]['dateList'][0]['selectCourseList'][index]['timeAndPlaceList'][index1][
                'continuingSession']
            classWeek = temp[0]['dateList'][0]['selectCourseList'][index]['timeAndPlaceList'][index1]['classDay']
            classWeekTimes = temp[0]['dateList'][0]['selectCourseList'][index]['timeAndPlaceList'][index1][
                'weekDescription'].split(',')
            for index3 in range(len(classWeekTimes)):
                VEVENT = ''
                VEVENT += 'BEGIN:VEVENT\n'
                # 周次
                WeekTimes = re.findall(r"\d+\.?\d*", classWeekTimes[index3])
                # 开始周
                delta = datetime.timedelta(weeks=int(WeekTimes[0]) - 1)
                # 开始星期
                delta += datetime.timedelta(days=int(classWeek) - 1)
                classStartTime = beginDate + delta
                # 开始日期
                classStartDate = beginDate + delta
                # 开始时间
                classStartTime = datetime.datetime.strptime(
                    startTime[int(classSession)], '%H:%M').time()
                # 结束时间
                classEndTime = datetime.datetime.strptime(
                    endTime[int(classSession) + int(classAmount) - 1], '%H:%M').time()
                # 最终开始时间
                classStartDateTime = datetime.datetime.combine(
                    classStartDate, classStartTime)
                # 最终结束时间
                classEndDateTime = datetime.datetime.combine(
                    classStartDate, classEndTime)
                # 写入开始时间
                VEVENT += 'DTSTART;TZID=Asia/Shanghai:{classStartDateTime}\n'.format(
                    classStartDateTime=classStartDateTime.strftime(
                        '%Y%m%dT%H%M%S'))
                # 写入结束时间
                VEVENT += 'DTEND;TZID=Asia/Shanghai:{classEndDateTime}\n'.format(
                    classEndDateTime=classEndDateTime.strftime(
                        '%Y%m%dT%H%M%S'))

                # 设置循环
                if '-' in classWeekTimes[index3]:
                    VEVENT += 'RRULE:FREQ=WEEKLY;WKST=MO;COUNT={count};BYDAY={byday}\n'.format(count=str(
                        int(WeekTimes[1]) - int(WeekTimes[0]) + 1), byday=weekName[int(classWeek)])
                else:
                    interval = int(WeekTimes[0])
                    VEVENT += 'RRULE:FREQ=WEEKLY;WKST=MO;COUNT={count};INTERVAL={interval};BYDAY={byday}\n'.format(
                        count=1, interval=str(interval), byday=weekName[int(classWeek)])

                # 地点
                VEVENT += ('LOCATION:' + classBuilding + classRoom + '\n')
                # 名称
                VEVENT += ('SUMMARY:' + className + '\n')
                VEVENT += 'END:VEVENT\n'
                file.write(VEVENT)

    file.write('END:VCALENDAR')
    file.close()
f.close()
print('Finished, check code directory!')
os.system('pause')
