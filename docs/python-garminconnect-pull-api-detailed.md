# Python GarminConnect Pull API Detailed Reference

- 范围: `Garmin` class pull interfaces only (`get_*` + `download_*`)
- 接口总数: 88
- 源码快照: `edcf79f776f9e24ee780e48a2f623b33ecfbfc5f`
- 说明: 输出样例为代表性字段示例（节选），实际响应会因账号、设备和功能开通情况而变化。

## 认证初始化

```python
from garminconnect import Garmin

api = Garmin(email='your_email', password='your_password', is_cn=False)
api.login()
```

## User & Profile (4)

### `get_full_name()`

- 说明: Return full name.
- 返回类型: `str | None`
- 输入样例:
```python
api.get_full_name()
```
- 输出样例:
```json
"Alex Runner"
```

### `get_unit_system()`

- 说明: Return unit system.
- 返回类型: `str | None`
- 输入样例:
```python
api.get_unit_system()
```
- 输出样例:
```json
"metric"
```

### `get_user_profile()`

- 说明: Get all users settings.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_user_profile()
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_userprofile_settings()`

- 说明: Get user settings.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_userprofile_settings()
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

## Daily Health & Activity (9)

### `get_all_day_stress(cdate)`

- 说明: Return available all day stress data 'cdate' format 'YYYY-MM-DD'.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_all_day_stress(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "calendarDate": "2026-02-09",
  "stressValues": [
    [
      1739059200000,
      21
    ]
  ]
}
```

### `get_heart_rates(cdate)`

- 说明: Fetch available heart rates data 'cDate' format 'YYYY-MM-DD'.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_heart_rates(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "lastSevenDaysAvgRestingHeartRate": 52,
  "heartRateValues": [
    [
      1739059200000,
      58
    ],
    [
      1739059500000,
      62
    ]
  ]
}
```

### `get_lifestyle_logging_data(cdate)`

- 说明: Return lifestyle logging data for current user.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_lifestyle_logging_data(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_rhr_day(cdate)`

- 说明: Return resting heartrate data for current user.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_rhr_day(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_sleep_data(cdate)`

- 说明: Return sleep data for current user.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_sleep_data(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "dailySleepDTO": {
    "sleepStartTimestampGMT": 1739052000000,
    "sleepEndTimestampGMT": 1739077200000,
    "sleepTimeSeconds": 25200
  }
}
```

### `get_stats(cdate)`

- 说明: Return user activity summary for 'cdate' format 'YYYY-MM-DD'
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_stats(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_stats_and_body(cdate)`

- 说明: Return activity data and body composition (compat for garminconnect).
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_stats_and_body(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_steps_data(cdate)`

- 说明: Fetch available steps data 'cDate' format 'YYYY-MM-DD'.
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_steps_data(cdate='2026-02-09')
```
- 输出样例:
```json
[
  {
    "startGMT": "2026-02-09T00:00:00.0",
    "endGMT": "2026-02-09T00:15:00.0",
    "steps": 112
  }
]
```

### `get_user_summary(cdate)`

- 说明: Return user activity summary for 'cdate' format 'YYYY-MM-DD'.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_user_summary(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "calendarDate": "2026-02-09",
  "totalSteps": 12345,
  "totalDistanceMeters": 8421.5,
  "activeKilocalories": 560
}
```

## Advanced Health Metrics (11)

### `get_fitnessage_data(cdate)`

- 说明: Return Fitness Age data for current user.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_fitnessage_data(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_hrv_data(cdate)`

- 说明: Return Heart Rate Variability (hrv) data for current user.
- 返回类型: `dict[str, Any] | None`
- 输入样例:
```python
api.get_hrv_data(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "calendarDate": "2026-02-09",
  "hrvBaseline": 58,
  "hrvReadings": [
    61,
    57,
    59
  ]
}
```

### `get_intensity_minutes_data(cdate)`

- 说明: Return available Intensity Minutes data 'cdate' format 'YYYY-MM-DD'.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_intensity_minutes_data(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_lactate_threshold(latest=True, start_date=None, end_date=None, aggregation='daily')`

- 说明: Returns Running Lactate Threshold information, including heart rate, power, and speed.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_lactate_threshold(latest=True, start_date='2026-02-09', end_date='2026-02-09', aggregation='daily')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_max_metrics(cdate)`

- 说明: Return available max metric data for 'cdate' format 'YYYY-MM-DD'.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_max_metrics(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_morning_training_readiness(cdate)`

- 说明: Return morning training readiness data for current user.
- 返回类型: `dict[str, Any] | None`
- 输入样例:
```python
api.get_morning_training_readiness(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_respiration_data(cdate)`

- 说明: Return available respiration data 'cdate' format 'YYYY-MM-DD'.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_respiration_data(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_spo2_data(cdate)`

- 说明: Return available SpO2 data 'cdate' format 'YYYY-MM-DD'.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_spo2_data(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "calendarDate": "2026-02-09",
  "averageSpo2": 97
}
```

### `get_stress_data(cdate)`

- 说明: Return stress data for current user.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_stress_data(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "calendarDate": "2026-02-09",
  "stressValues": [
    [
      1739059200000,
      21
    ]
  ]
}
```

### `get_training_readiness(cdate)`

- 说明: Return training readiness data for current user.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_training_readiness(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_training_status(cdate)`

- 说明: Return training status data for current user.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_training_status(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

## Historical Data & Trends (9)

### `get_blood_pressure(startdate, enddate=None)`

- 说明: Returns blood pressure by day for 'startdate' format
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_blood_pressure(startdate='2026-02-09', enddate='2026-02-09')
```
- 输出样例:
```json
{
  "measurements": [
    {
      "systolic": 118,
      "diastolic": 76,
      "pulse": 58
    }
  ],
  "total": 1
}
```

### `get_body_battery(startdate, enddate=None)`

- 说明: Return body battery values by day for 'startdate' format
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_body_battery(startdate='2026-02-09', enddate='2026-02-09')
```
- 输出样例:
```json
[
  {
    "id": "sample-id",
    "name": "sample-name"
  }
]
```

### `get_body_battery_events(cdate)`

- 说明: Return body battery events for date 'cdate' format 'YYYY-MM-DD'.
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_body_battery_events(cdate='2026-02-09')
```
- 输出样例:
```json
[
  {
    "id": "sample-id",
    "name": "sample-name"
  }
]
```

### `get_daily_steps(start, end)`

- 说明: Fetch available steps data 'start' and 'end' format 'YYYY-MM-DD'.
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_daily_steps(start='2026-02-09', end='2026-02-09')
```
- 输出样例:
```json
[
  {
    "id": "sample-id",
    "name": "sample-name"
  }
]
```

### `get_floors(cdate)`

- 说明: Fetch available floors data 'cDate' format 'YYYY-MM-DD'.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_floors(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_progress_summary_between_dates(startdate, enddate, metric='distance', groupbyactivities=True)`

- 说明: Fetch progress summary data between specific dates
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_progress_summary_between_dates(startdate='2026-02-09', enddate='2026-02-09', metric='distance', groupbyactivities=True)
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_weekly_intensity_minutes(start, end)`

- 说明: Fetch weekly intensity minutes aggregates.
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_weekly_intensity_minutes(start='2026-02-09', end='2026-02-09')
```
- 输出样例:
```json
[
  {
    "id": "sample-id",
    "name": "sample-name"
  }
]
```

### `get_weekly_steps(end, weeks=52)`

- 说明: Fetch weekly steps aggregates.
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_weekly_steps(end='2026-02-09', weeks=52)
```
- 输出样例:
```json
[
  {
    "id": "sample-id",
    "name": "sample-name"
  }
]
```

### `get_weekly_stress(end, weeks=52)`

- 说明: Fetch weekly stress aggregates.
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_weekly_stress(end='2026-02-09', weeks=52)
```
- 输出样例:
```json
[
  {
    "id": "sample-id",
    "name": "sample-name"
  }
]
```

## Activities & Workouts (21)

### `download_activity(activity_id, dl_fmt=ActivityDownloadFormat.TCX)`

- 说明: Downloads activity in requested format and returns the raw bytes. For
- 返回类型: `bytes`
- 输入样例:
```python
api.download_activity(activity_id='1234567890', dl_fmt=Garmin.ActivityDownloadFormat.TCX)
```
- 输出样例:
```json
"<bytes: TCX/GPX/KML/ZIP content>"
```

### `download_workout(workout_id)`

- 说明: Download workout by id.
- 返回类型: `bytes`
- 输入样例:
```python
api.download_workout(workout_id=12345)
```
- 输出样例:
```json
"<bytes: FIT content>"
```

### `get_activities(start=0, limit=20, activitytype=None)`

- 说明: Return available activities.
- 返回类型: `dict[str, Any] | list[Any]`
- 输入样例:
```python
api.get_activities(start=0, limit=20, activitytype='running')
```
- 输出样例:
```json
[
  {
    "activityId": 1234567890,
    "activityName": "Morning Run",
    "activityType": {
      "typeKey": "running"
    },
    "distance": 10000.0
  }
]
```

### `get_activities_by_date(startdate, enddate=None, activitytype=None, sortorder=None)`

- 说明: Fetch available activities between specific dates
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_activities_by_date(startdate='2026-02-09', enddate='2026-02-09', activitytype='running', sortorder='asc')
```
- 输出样例:
```json
[
  {
    "id": "sample-id",
    "name": "sample-name"
  }
]
```

### `get_activities_fordate(fordate)`

- 说明: Return available activities for date.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_activities_fordate(fordate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_activity(activity_id)`

- 说明: Return activity summary, including basic splits.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_activity(activity_id='1234567890')
```
- 输出样例:
```json
{
  "activityId": 1234567890,
  "activityName": "Morning Run",
  "duration": 2880.0,
  "distance": 10000.0
}
```

### `get_activity_details(activity_id, maxchart=2000, maxpoly=4000)`

- 说明: Return activity details.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_activity_details(activity_id='1234567890', maxchart=2000, maxpoly=4000)
```
- 输出样例:
```json
{
  "activityId": 1234567890,
  "name": "sample activity",
  "summary": {
    "distance": 5000
  }
}
```

### `get_activity_exercise_sets(activity_id)`

- 说明: Return activity exercise sets.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_activity_exercise_sets(activity_id='1234567890')
```
- 输出样例:
```json
{
  "activityId": 1234567890,
  "name": "sample activity",
  "summary": {
    "distance": 5000
  }
}
```

### `get_activity_gear(activity_id)`

- 说明: Return gears used for activity id.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_activity_gear(activity_id='1234567890')
```
- 输出样例:
```json
{
  "activityId": 1234567890,
  "name": "sample activity",
  "summary": {
    "distance": 5000
  }
}
```

### `get_activity_hr_in_timezones(activity_id)`

- 说明: Return activity heartrate in timezones.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_activity_hr_in_timezones(activity_id='1234567890')
```
- 输出样例:
```json
{
  "activityId": 1234567890,
  "name": "sample activity",
  "summary": {
    "distance": 5000
  }
}
```

### `get_activity_power_in_timezones(activity_id)`

- 说明: Return activity power in timezones.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_activity_power_in_timezones(activity_id='1234567890')
```
- 输出样例:
```json
{
  "activityId": 1234567890,
  "name": "sample activity",
  "summary": {
    "distance": 5000
  }
}
```

### `get_activity_split_summaries(activity_id)`

- 说明: Return activity split summaries.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_activity_split_summaries(activity_id='1234567890')
```
- 输出样例:
```json
{
  "activityId": 1234567890,
  "name": "sample activity",
  "summary": {
    "distance": 5000
  }
}
```

### `get_activity_splits(activity_id)`

- 说明: Return activity splits.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_activity_splits(activity_id='1234567890')
```
- 输出样例:
```json
{
  "activityId": 1234567890,
  "name": "sample activity",
  "summary": {
    "distance": 5000
  }
}
```

### `get_activity_typed_splits(activity_id)`

- 说明: Return typed activity splits. Contains similar info to `get_activity_splits`, but for certain activity types
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_activity_typed_splits(activity_id='1234567890')
```
- 输出样例:
```json
{
  "activityId": 1234567890,
  "name": "sample activity",
  "summary": {
    "distance": 5000
  }
}
```

### `get_activity_types()`

- 说明: No inline docstring.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_activity_types()
```
- 输出样例:
```json
{
  "activityId": 1234567890,
  "name": "sample activity",
  "summary": {
    "distance": 5000
  }
}
```

### `get_activity_weather(activity_id)`

- 说明: Return activity weather.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_activity_weather(activity_id='1234567890')
```
- 输出样例:
```json
{
  "activityId": 1234567890,
  "name": "sample activity",
  "summary": {
    "distance": 5000
  }
}
```

### `get_cycling_ftp()`

- 说明: Return cycling Functional Threshold Power (FTP) information.
- 返回类型: `dict[str, Any] | list[dict[str, Any]]`
- 输入样例:
```python
api.get_cycling_ftp()
```
- 输出样例:
```json
[
  {
    "id": "sample-id",
    "name": "sample-name"
  }
]
```

### `get_last_activity()`

- 说明: Return last activity.
- 返回类型: `dict[str, Any] | None`
- 输入样例:
```python
api.get_last_activity()
```
- 输出样例:
```json
{
  "activityId": 1234567890,
  "name": "sample activity",
  "summary": {
    "distance": 5000
  }
}
```

### `get_scheduled_workout_by_id(scheduled_workout_id)`

- 说明: Return scheduled workout by ID.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_scheduled_workout_by_id(scheduled_workout_id=12345)
```
- 输出样例:
```json
{
  "workoutId": 12345,
  "workoutName": "sample workout"
}
```

### `get_workout_by_id(workout_id)`

- 说明: Return workout by id.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_workout_by_id(workout_id=12345)
```
- 输出样例:
```json
{
  "workoutId": 12345,
  "workoutName": "sample workout"
}
```

### `get_workouts(start=0, limit=100)`

- 说明: Return workouts starting at offset `start` with at most `limit` results.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_workouts(start=0, limit=100)
```
- 输出样例:
```json
{
  "workouts": [
    {
      "workoutId": 12345,
      "workoutName": "Tempo Run"
    }
  ],
  "total": 1
}
```

## Body Composition & Weight (3)

### `get_body_composition(startdate, enddate=None)`

- 说明: Return available body composition data for 'startdate' format
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_body_composition(startdate='2026-02-09', enddate='2026-02-09')
```
- 输出样例:
```json
{
  "date": "2026-02-09",
  "weight": 68.4,
  "percentFat": 16.8,
  "muscleMass": 54.2
}
```

### `get_daily_weigh_ins(cdate)`

- 说明: Get weigh-ins for 'cdate' format 'YYYY-MM-DD'.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_daily_weigh_ins(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_weigh_ins(startdate, enddate)`

- 说明: Get weigh-ins between startdate and enddate using format 'YYYY-MM-DD'.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_weigh_ins(startdate='2026-02-09', enddate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

## Goals & Achievements (13)

### `get_adhoc_challenges(start, limit)`

- 说明: Return adhoc challenges for current user.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_adhoc_challenges(start='2026-02-09', limit=20)
```
- 输出样例:
```json
{
  "items": [
    {
      "id": 1,
      "name": "sample"
    }
  ],
  "total": 1
}
```

### `get_available_badge_challenges(start, limit)`

- 说明: Return available badge challenges.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_available_badge_challenges(start='2026-02-09', limit=20)
```
- 输出样例:
```json
{
  "items": [
    {
      "id": 1,
      "name": "sample"
    }
  ],
  "total": 1
}
```

### `get_available_badges()`

- 说明: Return available badges for current user.
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_available_badges()
```
- 输出样例:
```json
[
  {
    "id": "sample-id",
    "name": "sample-name"
  }
]
```

### `get_badge_challenges(start, limit)`

- 说明: Return badge challenges for current user.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_badge_challenges(start='2026-02-09', limit=20)
```
- 输出样例:
```json
{
  "items": [
    {
      "id": 1,
      "name": "sample"
    }
  ],
  "total": 1
}
```

### `get_earned_badges()`

- 说明: Return earned badges for current user.
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_earned_badges()
```
- 输出样例:
```json
[
  {
    "id": "sample-id",
    "name": "sample-name"
  }
]
```

### `get_endurance_score(startdate, enddate=None)`

- 说明: Return endurance score by day for 'startdate' format 'YYYY-MM-DD'
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_endurance_score(startdate='2026-02-09', enddate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_goals(status='active', start=0, limit=30)`

- 说明: Fetch all goals based on status
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_goals(status='active', start=0, limit=30)
```
- 输出样例:
```json
{
  "goals": [
    {
      "goalId": 111,
      "metric": "steps",
      "targetValue": 10000,
      "status": "active"
    }
  ],
  "total": 1
}
```

### `get_hill_score(startdate, enddate=None)`

- 说明: Return hill score by day from 'startdate' format 'YYYY-MM-DD'
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_hill_score(startdate='2026-02-09', enddate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_in_progress_badges()`

- 说明: Return in progress badges for current user.
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_in_progress_badges()
```
- 输出样例:
```json
[
  {
    "id": "sample-id",
    "name": "sample-name"
  }
]
```

### `get_inprogress_virtual_challenges(start, limit)`

- 说明: Return in-progress virtual challenges for current user.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_inprogress_virtual_challenges(start='2026-02-09', limit=20)
```
- 输出样例:
```json
{
  "items": [
    {
      "id": 1,
      "name": "sample"
    }
  ],
  "total": 1
}
```

### `get_non_completed_badge_challenges(start, limit)`

- 说明: Return badge non-completed challenges for current user.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_non_completed_badge_challenges(start='2026-02-09', limit=20)
```
- 输出样例:
```json
{
  "items": [
    {
      "id": 1,
      "name": "sample"
    }
  ],
  "total": 1
}
```

### `get_personal_record()`

- 说明: Return personal records for current user.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_personal_record()
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_race_predictions(startdate=None, enddate=None, _type=None)`

- 说明: Return race predictions for the 5k, 10k, half marathon and marathon.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_race_predictions(startdate='2026-02-09', enddate='2026-02-09', _type='running')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

## Device & Technical (6)

### `get_device_alarms()`

- 说明: Get list of active alarms from all devices.
- 返回类型: `list[Any]`
- 输入样例:
```python
api.get_device_alarms()
```
- 输出样例:
```json
[
  "item1",
  "item2"
]
```

### `get_device_last_used()`

- 说明: Return device last used.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_device_last_used()
```
- 输出样例:
```json
{
  "userProfileNumber": 12345678,
  "deviceId": 123456,
  "lastUsedDate": "2026-02-09"
}
```

### `get_device_settings(device_id)`

- 说明: Return device settings for device with 'device_id'.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_device_settings(device_id='123456')
```
- 输出样例:
```json
{
  "deviceId": 123456,
  "settings": {
    "language": "en_US",
    "timeFormat": "24h"
  }
}
```

### `get_device_solar_data(device_id, startdate, enddate=None)`

- 说明: Return solar data for compatible device with 'device_id'.
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_device_solar_data(device_id='123456', startdate='2026-02-09', enddate='2026-02-09')
```
- 输出样例:
```json
[
  {
    "id": "sample-id",
    "name": "sample-name"
  }
]
```

### `get_devices()`

- 说明: Return available devices for the current user account.
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_devices()
```
- 输出样例:
```json
[
  {
    "deviceId": 123456,
    "displayName": "Forerunner 965",
    "lastUsedTime": "2026-02-09T07:20:00"
  }
]
```

### `get_primary_training_device()`

- 说明: Return detailed information around primary training devices, included the specified device and the
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_primary_training_device()
```
- 输出样例:
```json
{
  "deviceId": 123456,
  "displayName": "sample device"
}
```

## Gear & Equipment (4)

### `get_gear(userProfileNumber)`

- 说明: Return all user gear.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_gear(userProfileNumber='12345678')
```
- 输出样例:
```json
[
  {
    "uuid": "gear-uuid-1234",
    "displayName": "Pegasus 41",
    "totalDistance": 412345
  }
]
```

### `get_gear_activities(gearUUID, limit=1000)`

- 说明: Return activities where gear uuid was used.
- 返回类型: `list[dict[str, Any]]`
- 输入样例:
```python
api.get_gear_activities(gearUUID='gear-uuid-1234', limit=1000)
```
- 输出样例:
```json
[
  {
    "id": "sample-id",
    "name": "sample-name"
  }
]
```

### `get_gear_defaults(userProfileNumber)`

- 说明: No inline docstring.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_gear_defaults(userProfileNumber='12345678')
```
- 输出样例:
```json
{
  "uuid": "gear-uuid-1234",
  "displayName": "sample gear"
}
```

### `get_gear_stats(gearUUID)`

- 说明: No inline docstring.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_gear_stats(gearUUID='gear-uuid-1234')
```
- 输出样例:
```json
{
  "uuid": "gear-uuid-1234",
  "numberOfActivities": 57,
  "distance": 412345,
  "duration": 1234567
}
```

## Hydration & Wellness (5)

### `get_all_day_events(cdate)`

- 说明: Return available daily events data 'cdate' format 'YYYY-MM-DD'.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_all_day_events(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_hydration_data(cdate)`

- 说明: Return available hydration data 'cdate' format 'YYYY-MM-DD'.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_hydration_data(cdate='2026-02-09')
```
- 输出样例:
```json
{
  "calendarDate": "2026-02-09",
  "valueInML": 1800,
  "goalInML": 2500
}
```

### `get_menstrual_calendar_data(startdate, enddate)`

- 说明: Return summaries of cycles that have days between startdate and enddate.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_menstrual_calendar_data(startdate='2026-02-09', enddate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_menstrual_data_for_date(fordate)`

- 说明: Return menstrual data for date.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_menstrual_data_for_date(fordate='2026-02-09')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_pregnancy_summary()`

- 说明: Return snapshot of pregnancy data.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_pregnancy_summary()
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

## Training Plans (3)

### `get_adaptive_training_plan_by_id(plan_id)`

- 说明: Return details for a specific adaptive training plan.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_adaptive_training_plan_by_id(plan_id='sample')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_training_plan_by_id(plan_id)`

- 说明: Return details for a specific training plan.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_training_plan_by_id(plan_id='sample')
```
- 输出样例:
```json
{
  "status": "ok",
  "data": "sample"
}
```

### `get_training_plans()`

- 说明: Return all available training plans.
- 返回类型: `dict[str, Any]`
- 输入样例:
```python
api.get_training_plans()
```
- 输出样例:
```json
{
  "trainingPlanList": [
    {
      "trainingPlanId": 101,
      "name": "10K Plan",
      "trainingPlanCategory": "FBT_STATIC"
    }
  ]
}
```

