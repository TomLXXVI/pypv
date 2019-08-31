import sun

points_hp01 = [
    sun.HorizonPoint(label='1', planar_distance=93.0, azimuth=60.0, elevation=10.4),
    sun.HorizonPoint(label='2', planar_distance=113.0, azimuth=67.0, elevation=15.8),
    sun.HorizonPoint(label='3', planar_distance=104.0, azimuth=74.0, elevation=13.1),
    sun.HorizonPoint(label='4', planar_distance=13.0, azimuth=80.0, elevation=21.8),
    sun.HorizonPoint(label='5', planar_distance=12.0, azimuth=86.0, elevation=22.2),
    sun.HorizonPoint(label='6', planar_distance=12.0, azimuth=87.0, elevation=28.7),
    sun.HorizonPoint(label='7', planar_distance=12.0, azimuth=99.0, elevation=29.9),
    sun.HorizonPoint(label='8', planar_distance=12.0, azimuth=112.0, elevation=29.8),
    sun.HorizonPoint(label='9', planar_distance=12.0, azimuth=117.0, elevation=21.1),
    sun.HorizonPoint(label='10', planar_distance=7.0, azimuth=131.1, elevation=10.6),
    sun.HorizonPoint(label='11', planar_distance=7.0, azimuth=136.0, elevation=11.3),
    sun.HorizonPoint(label='12', planar_distance=11.0, azimuth=140.0, elevation=26.4),
    sun.HorizonPoint(label='13', planar_distance=12.0, azimuth=162.1, elevation=27.3),
    sun.HorizonPoint(label='14', planar_distance=13.0, azimuth=203.0, elevation=20.6),
    sun.HorizonPoint(label='15', planar_distance=20.0, azimuth=205.0, elevation=15.6),
    sun.HorizonPoint(label='16', planar_distance=28.0, azimuth=226.0, elevation=12.3),
    sun.HorizonPoint(label='17', planar_distance=34.0, azimuth=229.0, elevation=5.7),
    sun.HorizonPoint(label='18', planar_distance=44.0, azimuth=238.0, elevation=4.7),
    sun.HorizonPoint(label='19', planar_distance=59.0, azimuth=246.0, elevation=1.4),
    sun.HorizonPoint(label='20', planar_distance=66.0, azimuth=251.0, elevation=3.8),
    sun.HorizonPoint(label='21', planar_distance=70.0, azimuth=255.0, elevation=5.1),
    sun.HorizonPoint(label='22', planar_distance=63.0, azimuth=260.0, elevation=1.8),
]
for pnt in points_hp01: pnt.move_viewpoint(0.0, 0.0, -1.7)
hp_01 = sun.HorizonProfile(points_hp01)


points_hp02 = [
    sun.HorizonPoint(label='1', planar_distance=140.0, azimuth=70.0, elevation=15.5),
    sun.HorizonPoint(label='2', planar_distance=56.0, azimuth=80.0, elevation=7.0),
    sun.HorizonPoint(label='3', planar_distance=50.0, azimuth=83.0, elevation=7.1),
    sun.HorizonPoint(label='4', planar_distance=75.0, azimuth=81.0, elevation=13.2),
    sun.HorizonPoint(label='5', planar_distance=115.0, azimuth=91.0, elevation=13.4),
    sun.HorizonPoint(label='6', planar_distance=104.0, azimuth=108.0, elevation=18.1),
    sun.HorizonPoint(label='7', planar_distance=15.0, azimuth=110.0, elevation=22.8),
    sun.HorizonPoint(label='8', planar_distance=13.0, azimuth=125.0, elevation=22.9),
    sun.HorizonPoint(label='9', planar_distance=13.0, azimuth=138.0, elevation=6.6),
    sun.HorizonPoint(label='10', planar_distance=87.0, azimuth=138.1, elevation=12.4),
    sun.HorizonPoint(label='11', planar_distance=48.0, azimuth=163.0, elevation=21.4),
    sun.HorizonPoint(label='12', planar_distance=54.0, azimuth=175.0, elevation=20.7),
    sun.HorizonPoint(label='13', planar_distance=18.0, azimuth=175.1, elevation=18.4),
    sun.HorizonPoint(label='14', planar_distance=20.0, azimuth=192.0, elevation=17.2),
    sun.HorizonPoint(label='15', planar_distance=24.0, azimuth=197.0, elevation=14.7),
    sun.HorizonPoint(label='16', planar_distance=32.0, azimuth=217.0, elevation=11.2),
    sun.HorizonPoint(label='17', planar_distance=35.0, azimuth=223.0, elevation=4.1),
    sun.HorizonPoint(label='18', planar_distance=44.0, azimuth=236.0, elevation=4.9),
    sun.HorizonPoint(label='19', planar_distance=67.0, azimuth=255.0, elevation=4.9),
    sun.HorizonPoint(label='20', planar_distance=63.0, azimuth=257.0, elevation=2.0)
]
for pnt in points_hp02: pnt.move_viewpoint(0.0, 0.0, -1.7)
hp_02 = sun.HorizonProfile(points_hp02)
