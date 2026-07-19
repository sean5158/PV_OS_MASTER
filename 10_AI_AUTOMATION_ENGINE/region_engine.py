"""
PV_OS Region Engine V1.0

客户区域判断：
1. 平台IP属地
2. 评论主动城市表达
3. 区域评分
"""


def match_customer_region(comment: dict) -> dict:

    ip_location = comment.get("ip_location", "")
    content = comment.get("content", "")

    text = f"{ip_location} {content}"


    region = {
        "province": "",
        "city": "",
        "district": "",

        "source": [],

        "confidence": "LOW",

        "region_score": 5,

        "match_type": "",

        "ip_region": "",
        "comment_region": "",
    }


    # IP来源

    if ip_location:
        region["source"].append("ip_location")
        region["ip_region"] = ip_location

   
    # 评论来源

    if content:
        region["source"].append("comment_text")
        region["comment_region"] = content   
 


    # 城市匹配（V1）

    city_map = {

        "成都": "四川",
        "绵阳": "四川",
        "宜宾": "四川",
        "泸州": "四川",
        "南充": "四川",

        "重庆": "重庆",

        "贵阳": "贵州",
        "遵义": "贵州",

    }


    for city, province in city_map.items():

        if city in content:

            region["city"] = city
            region["province"] = province
            region["match_type"] = "comment_confirmed"
            region["region_score"] = 20
            break


        elif city in ip_location:

            region["city"] = city
            region["province"] = province
            region["match_type"] = "ip_confirmed"
            break



    # 省份判断

    if not region["province"]:

        if "四川" in text or "川" in text:
            region["province"] = "四川"

        elif "重庆" in text or "渝" in text:
            region["province"] = "重庆"

        elif "贵州" in text or "黔" in text:
            region["province"] = "贵州"



    # 评分

    if region["city"] == "成都":

        region["region_score"] = 18

    elif region["city"]:

        region["region_score"] = 16

    elif region["province"]:

        region["region_score"] = 10



    # 置信度

    if region["city"]:
        region["confidence"] = "MEDIUM"

    elif region["province"]:
        region["confidence"] = "LOW"


    return region
