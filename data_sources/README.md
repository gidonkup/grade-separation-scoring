# מקורות נתונים

הקבצים ב-`raw/` הם קבצי המקור המקוריים שהתקבלו, ללא עיבוד. `backend/scripts/build_reference_data.py`
קורא מהם ובונה את שכבות הרקע הסופיות ב-`backend/data/*.geojson`.

## `raw/traffic_zones/` — אזורי תנועה (TAZ)
מקור: `TAZ_V4_241103_with_geo_info.shp` (JTMT). 905 פוליגונים, מפתח חיבור: `Taz_num`.

## `raw/population_employment_forecast_2020_2050.xlsx`
מקור: `250630_forecast_2020_till_2050_jtmt.xlsx`. תחזית אוכלוסין ומועסקים לכל אזור תנועה
(`Taz_num`), לשנים 2020 עד 2050. העמודות שבשימוש כרגע (שנת בסיס 2020):
- `pop_without_dorms_yeshiva` — אוכלוסייה (ללא מעונות/ישיבות)
- `total_emp` — סה"כ מועסקים

לשנים אחרות יש עמודות עם סיומת `_2025`, `_2030` וכו' - עדיין לא מחוברות לכלי.

## `raw/built_up_area/` — שטח בנוי
מקור: `bld_area__il_2018_marag.shp`. שכבה ארצית אחת (מרכז מיפוי ישראל, 2018) - פוליגון ענק
ולא תקין טופולוגית שמכיל את כל שטחי הבינוי בישראל. `build_reference_data.py` מפרק אותו
לחלקים, מסנן לאזור ירושלים, ורק אז מתקן תקינות (ראו הערה בקוד - תיקון על השכבה כולה
לוקח 10+ דקות).

## `raw/junctions_layer/` — צמתים
מקור: `junctions.shp` (כנראה מבוסס OSM). 268,792 נקודות ברחבי הארץ, שדה `degree` (כל
הרשומות degree>=3, כלומר כבר רק צמתים אמיתיים ולא נקודות אמצע-קטע). מסונן לאזור ירושלים
באותו אופן כמו שטח בנוי.

## פלט: `backend/data/*.geojson`
- `traffic_zones.geojson` — שדות `zone_id`, `zone_name`, `population_2020`, `employment_2020`.
- `built_up_area.geojson` — גיאומטריה בלבד, מסונן לאזור ירושלים.
- `intersections.geojson` — **נתונים אמיתיים** (מ-`junctions_layer`), מסונן לאזור ירושלים.
