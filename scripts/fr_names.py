"""Chinese labels for the French atlas, with a pronunciation-based fallback."""
import ctypes
from functools import lru_cache
import os
from pathlib import Path
import re
import unicodedata
from zipfile import ZipFile

import espeakng_loader
from opencc import OpenCC


def key(text):
    decomposed = unicodedata.normalize("NFKD",text.casefold())
    return "".join(c for c in decomposed if c.isalnum())


REGIONS = dict(pair.split("|") for pair in """
Île-de-France|法兰西岛
Centre-Val de Loire|中央-卢瓦尔河谷
Bourgogne-Franche-Comté|勃艮第-弗朗什-孔泰
Normandie|诺曼底
Hauts-de-France|上法兰西
Grand Est|大东部
Pays de la Loire|卢瓦尔河地区
Bretagne|布列塔尼
Nouvelle-Aquitaine|新阿基坦
Occitanie|奥克西塔尼
Auvergne-Rhône-Alpes|奥弗涅-罗讷-阿尔卑斯
Provence-Alpes-Côte d'Azur|普罗旺斯-阿尔卑斯-蓝色海岸
Corse|科西嘉
Guadeloupe|瓜德罗普
Martinique|马提尼克
Guyane|法属圭亚那
La Réunion|留尼汪
Mayotte|马约特
""".strip().splitlines())

COMMON = dict(pair.split("|") for pair in """
Paris|巴黎
Marseille|马赛
Lyon|里昂
Nice|尼斯
Bordeaux|波尔多
Toulouse|图卢兹
Lille|里尔
Strasbourg|斯特拉斯堡
Nantes|南特
Rennes|雷恩
Rouen|鲁昂
Orléans|奥尔良
Montpellier|蒙彼利埃
Grenoble|格勒诺布尔
Dijon|第戎
Reims|兰斯
Metz|梅斯
Nancy|南锡
Besançon|贝桑松
Amiens|亚眠
Caen|卡昂
Chartres|沙特尔
Versailles|凡尔赛
Nanterre|楠泰尔
Évry|埃夫里
Cergy|塞尔吉
Saint-Denis|圣但尼
Le Havre|勒阿弗尔
La Rochelle|拉罗谢尔
Brest|布雷斯特
Quimper|坎佩尔
Limoges|利摩日
Clermont-Ferrand|克莱蒙费朗
Saint-Étienne|圣艾蒂安
Cannes|戛纳
Annecy|阿讷西
Avignon|阿维尼翁
Arles|阿尔勒
Nîmes|尼姆
Mont Saint-Michel|圣米歇尔山
Mulhouse|米卢斯
Colmar|科尔马
Perpignan|佩皮尼昂
Tours|图尔
Toulon|土伦
Angers|昂热
Poitiers|普瓦捷
Le Mans|勒芒
Ajaccio|阿雅克肖
Bastia|巴斯蒂亚
Cayenne|卡宴
Fort-de-France|法兰西堡
Mamoudzou|马穆楚
Basse-Terre|巴斯特尔
Pointe-à-Pitre|皮特尔角城
Rhône|罗讷
Seine|塞纳
Garonne|加龙
Loire|卢瓦尔
Alpes|阿尔卑斯
Pyrénées|比利牛斯
Côte d'Azur|蓝色海岸
Ain|安
Aisne|埃纳
Allier|阿列
Alpes-de-Haute-Provence|上普罗旺斯阿尔卑斯
Hautes-Alpes|上阿尔卑斯
Alpes-Maritimes|滨海阿尔卑斯
Ardèche|阿尔代什
Ardennes|阿登
Ariège|阿列日
Aube|奥布
Aude|奥德
Aveyron|阿韦龙
Bouches-du-Rhône|罗讷河口
Calvados|卡尔瓦多斯
Cantal|康塔尔
Charente|夏朗德
Charente-Maritime|滨海夏朗德
Cher|谢尔
Corrèze|科雷兹
Corse-du-Sud|南科西嘉
Haute-Corse|上科西嘉
Côte-d'Or|科多尔
Côtes-d'Armor|阿摩尔滨海
Creuse|克勒兹
Dordogne|多尔多涅
Doubs|杜
Drôme|德龙
Eure|厄尔
Eure-et-Loir|厄尔-卢瓦尔
Finistère|菲尼斯泰尔
Gard|加尔
Haute-Garonne|上加龙
Gers|热尔
Gironde|吉伦特
Hérault|埃罗
Ille-et-Vilaine|伊勒-维莱讷
Indre|安德尔
Indre-et-Loire|安德尔-卢瓦尔
Isère|伊泽尔
Jura|汝拉
Landes|朗德
Loir-et-Cher|卢瓦尔-谢尔
Haute-Loire|上卢瓦尔
Loire-Atlantique|大西洋卢瓦尔
Loiret|卢瓦雷
Lot|洛特
Lot-et-Garonne|洛特-加龙
Lozère|洛泽尔
Maine-et-Loire|曼恩-卢瓦尔
Manche|芒什
Marne|马恩
Haute-Marne|上马恩
Mayenne|马耶讷
Meurthe-et-Moselle|默尔特-摩泽尔
Meuse|默兹
Morbihan|莫尔比昂
Moselle|摩泽尔
Nièvre|涅夫勒
Nord|北方
Oise|瓦兹
Orne|奥恩
Pas-de-Calais|加来海峡
Puy-de-Dôme|多姆山
Pyrénées-Atlantiques|大西洋比利牛斯
Hautes-Pyrénées|上比利牛斯
Pyrénées-Orientales|东比利牛斯
Bas-Rhin|下莱茵
Haut-Rhin|上莱茵
Haute-Saône|上索恩
Saône-et-Loire|索恩-卢瓦尔
Sarthe|萨尔特
Savoie|萨瓦
Haute-Savoie|上萨瓦
Seine-Maritime|滨海塞纳
Seine-et-Marne|塞纳-马恩
Yvelines|伊夫林
Deux-Sèvres|德塞夫勒
Somme|索姆
Tarn|塔恩
Tarn-et-Garonne|塔恩-加龙
Var|瓦尔
Vaucluse|沃克吕兹
Vendée|旺代
Vienne|维埃纳
Haute-Vienne|上维埃纳
Vosges|孚日
Yonne|约讷
Territoire de Belfort|贝尔福地区
Essonne|埃松
Hauts-de-Seine|上塞纳
Seine-Saint-Denis|塞纳-圣但尼
Val-de-Marne|马恩河谷
Val-d'Oise|瓦兹河谷
Sorbonne Université|索邦大学
Université Paris Cité|巴黎西岱大学
Université Paris-Saclay|巴黎萨克雷大学
Université Paris 1 Panthéon-Sorbonne|巴黎第一大学
École polytechnique|巴黎综合理工学院
Sciences Po|巴黎政治学院
INSEAD|欧洲工商管理学院
HEC Paris|巴黎高等商学院
SKEMA Business School|斯凯玛商学院
ESCP Business School|欧洲高等商学院
EM Normandie Business School|诺曼底商学院
Côte Basque|巴斯克海岸
CentraleSupélec|巴黎中央理工-高等电力学院
Saint|圣
Sainte|圣
Université|大学
University|大学
Conservatoire|音乐学院
École|学院
Institut|研究院
Polytechnique|理工
Sciences|科学
Sciences politiques|政治学
Sciences humaines|人文学科
National|国立
Nationale|国立
Supérieur|高等
Supérieure|高等
Ingénieurs|工程师
Commerce|商学
Gestion|管理
Architecture|建筑
Beaux-Arts|美术
Arts|艺术
Médecine|医学
Technologie|技术
Design|设计
Commerciales|商学
Business School|商学院
Europe|欧洲
Sud|南部
Atlantique|大西洋
Méditerranée|地中海
Aéroport|机场
International Airport|国际机场
Airport|机场
International|国际
Gare|车站
TGV|高速铁路
Centre|中心
Rive gauche|左岸
Rive droite|右岸
Ville|市区
""".strip().splitlines())

VOWELS = dict(zip("aɑɛeəœøioɔuy","阿阿埃埃厄厄厄伊奥奥乌于"))
VOWELS.update({"ɑ̃":"昂","ɛ̃":"安","ɔ̃":"翁","œ̃":"恩","ã":"昂","ɐ":"阿","ʊ":"乌","ɪ":"伊","ʌ":"阿","ɚ":"尔"})
SYLLABLES = {
    "b":"巴贝比博布伯","p":"帕佩皮波普珀","d":"达德迪多杜德","t":"塔泰蒂托图特",
    "k":"卡凯基科库克","ɡ":"加盖吉戈古格","g":"加盖吉戈古格","f":"法费菲福富弗",
    "v":"瓦韦维沃武弗","s":"萨塞西索苏瑟","z":"扎泽齐佐祖泽","ʃ":"沙谢希绍舒舍",
    "ʒ":"扎热日若茹哲","m":"马梅米莫穆默","n":"纳内尼诺努讷","l":"拉莱利洛卢勒",
    "ʁ":"拉雷里罗鲁尔","r":"拉雷里罗鲁尔","w":"瓦韦威沃伍沃","j":"亚耶伊约尤耶",
    "ɥ":"于于于于于于","ɲ":"尼涅尼纽纽尼","h":"哈赫希霍胡赫","tʃ":"查切奇乔丘彻","dʒ":"贾杰吉乔朱杰"
}
TAILS = dict(zip("bpd tkɡgvfszʃʒmnlʁrŋ".replace(" ",""),"布普德特克格格夫夫斯兹什日姆恩尔尔尔昂"))
LETTER = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ","艾比西迪伊弗吉希艾杰凯尔艾恩欧皮丘阿艾蒂优维达艾怀泽"))
CHINESE = re.compile(r"^[\u3400-\u9fff·\- ]+$")
WORDS = re.compile(r"[^\W_]+(?:['’][^\W_]+)?",re.UNICODE)
REMOVABLE = {"de","du","des","d","le","la","les","l","en","et"}


class FrenchNames:
    def __init__(self,gazetteer):
        cc = OpenCC("t2s")
        self.names = {}
        ranking = {}
        with ZipFile(gazetteer) as archive, archive.open("FR.txt") as rows:
            for line in rows:
                row = line.decode("utf8").split("\t")
                if row[6] not in ("A","P","S"):
                    continue
                candidates = [name for name in row[3].split(",") if CHINESE.fullmatch(name)]
                if not candidates:
                    continue
                rank = (row[6] == "P",int(row[14] or 0))
                name = key(row[1])
                if ranking.get(name,(-1,0)) < rank:
                    self.names[name] = cc.convert(candidates[-1])
                    ranking[name] = rank
        self.names.update({key(a):b for a,b in (REGIONS|COMMON).items()})
        self.lib = espeakng_loader.load_library()
        self.lib.espeak_Initialize.argtypes = [ctypes.c_int,ctypes.c_int,ctypes.c_char_p,ctypes.c_int]
        self.lib.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]
        self.lib.espeak_TextToPhonemes.argtypes = [ctypes.POINTER(ctypes.c_char_p),ctypes.c_int,ctypes.c_int]
        self.lib.espeak_TextToPhonemes.restype = ctypes.c_char_p
        path = os.fsencode(Path(espeakng_loader.get_data_path()).parent)
        if self.lib.espeak_Initialize(2,0,path,0) <= 0 or self.lib.espeak_SetVoiceByName(b"fr"):
            raise RuntimeError("The French eSpeak voice is unavailable")

    @lru_cache(None)
    def pronounce(self,word):
        text = ctypes.c_char_p(word.encode("utf8"))
        raw = self.lib.espeak_TextToPhonemes(ctypes.byref(text),1,2|(ord("|")<<8)).decode()
        phones = re.findall(r"[^|ˈˌ .\-()]+",raw)
        parts, onset = [], []
        for phoneme in phones:
            phoneme = phoneme.rstrip("ː")
            if phoneme not in VOWELS:
                onset.append(phoneme)
                continue
            vowel = phoneme[0]
            bucket = 0 if vowel in "aɑʌ" else 1 if vowel in "ɛe" else 2 if vowel in "iɪ" else 3 if vowel in "ɔo" else 4 if vowel in "uyʊ" else 5
            parts.extend(TAILS.get(phone,"") for phone in onset[:-1])
            prefix = SYLLABLES.get(onset[-1]) if onset else None
            parts.append(prefix[bucket] if prefix else VOWELS[phoneme])
            if prefix and "̃" in phoneme:
                parts.append("昂" if vowel in "aɑɔ" else "恩")
            onset.clear()
        parts.extend(TAILS.get(phone,"") for phone in onset)
        return "".join(parts) or "".join(LETTER.get(ch.upper(),"") for ch in word)

    @lru_cache(None)
    def translate(self,label):
        label = label.strip()
        if key(label) in self.names:
            return self.names[key(label)]
        if CHINESE.fullmatch(label):
            return label
        words = WORDS.findall(re.sub(r"\b[dl][’'](?=\w)","",label,flags=re.I))
        translated = []
        index = 0
        while index < len(words):
            for end in range(min(index+6,len(words)),index,-1):
                term = self.names.get(key("".join(words[index:end])))
                if term:
                    translated.append(term)
                    index = end
                    break
            else:
                token = words[index]
                index += 1
                if key(token) in REMOVABLE:
                    continue
                if token.isdecimal():
                    translated.append(token)
                elif CHINESE.fullmatch(token):
                    translated.append(token)
                else:
                    translated.append(self.pronounce(token))
        return "".join(translated) or "未命名"

    def university(self,label):
        match = re.fullmatch(r"(?:Université|University)\s+(?:de\s+|d[’']\s*)?(.+)",label,re.I)
        if match and key(label) not in self.names:
            return self.translate(match[1])+"大学"
        match = re.fullmatch(r"École\s+(?:supérieure\s+)?(?:de\s+|d[’']\s*)?(.+)",label,re.I)
        if match and key(label) not in self.names:
            return self.translate(match[1])+("高等学院" if "supérieure" in label.casefold() else "学院")
        return self.translate(label)
