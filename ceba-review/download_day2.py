import sqlite3, os, shutil, requests
cookie_path = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Network\Cookies')
tmp = os.path.expandvars(r'%TEMP%\chrome_cookies.db')
shutil.copy2(cookie_path, tmp)
conn = sqlite3.connect(tmp)
c = conn.cursor()
c.execute("SELECT host_key, name, value FROM cookies WHERE host_key LIKE '%.google.com'")
cookies = {}
for row in c.fetchall():
    if 'docs.google.com' in row[0] or 'google.com' in row[0]:
        cookies[row[1]] = row[2]
conn.close()
os.remove(tmp)
print(f'Cookies found: {len(cookies)}')

url = 'https://docs.google.com/presentation/d/1IZTDsgYaJQDLKiiEk3oq4hkIaEG3BN3P8oI86i5-SR8/export/pptx'
out = r'C:\Users\tukum\Downloads\reopt-pysam\ceba-review\ENG_Draft_Day 2 July 2026_ Allotrope-CEBA Vietnam Clean Energy Procurement Academy In-Person Training Slides.pptx'

r = requests.get(url, cookies=cookies, allow_redirects=True, timeout=120)
print(f'Status: {r.status_code}')
print(f'Length: {len(r.content)}')
if len(r.content) > 10000:
    with open(out, 'wb') as f:
        f.write(r.content)
    print(f'Saved to: {out}')
else:
    print(r.text[:500])
