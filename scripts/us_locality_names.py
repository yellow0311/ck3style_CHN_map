"""Generate simplified Chinese labels for US municipalities and townships."""
import ctypes as c
from functools import lru_cache
import os
from pathlib import Path
import re
import unicodedata
from zipfile import ZipFile

import espeakng_loader as es
from opencc import OpenCC


lib = es.load_library()
lib.espeak_Initialize.argtypes = [c.c_int, c.c_int, c.c_char_p, c.c_int]
lib.espeak_SetVoiceByName.argtypes = [c.c_char_p]
lib.espeak_TextToPhonemes.argtypes = [c.POINTER(c.c_char_p), c.c_int, c.c_int]
lib.espeak_TextToPhonemes.restype = c.c_char_p
if lib.espeak_Initialize(2, 0, os.fsencode(Path(es.get_data_path()).parent), 0) <= 0:
    raise RuntimeError('Unable to initialize eSpeak data')
if lib.espeak_SetVoiceByName(b'en-us') != 0:
    raise RuntimeError('Unable to load the US English eSpeak voice')
vowels={
 'a':0,'æ':0,'ɑ':0,'ɑː':0,'ʌ':0,'ɛ':1,'e':1,'eɪ':1,'eə':1,'ɛː':1,'i':2,'iː':2,'ɪ':2,'ɪə':2,
 'ɔ':3,'ɒ':3,'ɔː':3,'əʊ':3,'oʊ':3,'oː':3,'u':4,'uː':4,'ʊ':4,'ʊə':4,'ə':5,'ɚ':5,'ɜː':5,'ɜ':5,
 'aɪ':6,'aʊ':7,'ɔɪ':8,'əl':5,'ən':5,'əm':5,'aɪə':6,'ɐ':0,'ɨ':2,'œ':5,'y':2,'ʏ':2,
}
table={
 '':'阿埃伊奥乌厄艾奥奥','b':'巴贝比博布伯拜鲍博','p':'帕佩皮波普珀派保波','d':'达德迪多杜德戴道多',
 't':'塔泰蒂托图特泰陶托','k':'卡凯基科库克凯考科','ɡ':'加盖吉戈古格盖高戈','f':'法费菲福富弗法福弗',
 'v':'瓦维维沃武弗瓦沃沃','s':'萨塞西索苏瑟赛骚索','z':'扎泽齐佐祖泽宰造佐','ʃ':'沙谢希绍舒舍沙绍绍',
 'ʒ':'扎热日若茹哲宰若若','tʃ':'查切奇乔丘彻柴乔乔','dʒ':'贾杰吉乔朱杰杰乔乔','h':'哈赫希霍胡赫海豪霍',
 'm':'马梅米莫穆默迈茂莫','n':'纳内尼诺努讷奈瑙诺','l':'拉莱利洛卢勒莱劳洛','ɹ':'拉雷里罗鲁尔赖劳罗',
 'w':'瓦韦威沃伍沃怀沃沃','j':'亚耶伊约尤耶耶约约','θ':'萨塞西索苏瑟赛骚索','ð':'达德迪多杜德戴道多','ɬ':'兰莱利洛卢勒莱劳洛',
 'x':'哈赫希霍胡赫海豪霍','ŋ':'昂恩因翁温恩艾昂翁',
}
tail={'b':'布','p':'普','d':'德','t':'特','k':'克','ɡ':'格','f':'夫','v':'夫','s':'斯','z':'兹','ʃ':'什','ʒ':'日','tʃ':'奇','dʒ':'奇','m':'姆','n':'恩','l':'尔','ɹ':'尔','θ':'思','ð':'斯','ŋ':'昂','h':'','w':'','j':'','ɬ':'尔','x':'赫'}
joint={'ba n':'班','be n':'本','bi n':'宾','bo n':'邦','bu n':'本','ma n':'曼','me n':'门','mi n':'明','mo n':'蒙','mu n':'蒙',
       'ka n':'坎','ke n':'肯','ki n':'金','ko n':'康','ku n':'昆','da n':'丹','de n':'登','di n':'丁','do n':'东','du n':'敦',
       'ta n':'坦','te n':'滕','ti n':'廷','to n':'通','tu n':'顿','la n':'兰','le n':'伦','li n':'林','lo n':'隆','lu n':'伦',
       'sa n':'桑','se n':'森','si n':'辛','so n':'松','ha n':'汉','he n':'亨','hi n':'欣','ho n':'洪','fa n':'凡','fe n':'芬','fi n':'芬',
       'pa n':'潘','pe n':'彭','pi n':'平','po n':'庞','na n':'南','ne n':'南','no n':'农','wa n':'万','we n':'温','wi n':'温',
       'a n':'安','e n':'恩','i n':'因','o n':'翁','u n':'温'}
letter=dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ','埃比西迪伊艾弗吉艾艾杰凯艾艾恩欧皮丘阿艾蒂优维达艾怀泽'))


@lru_cache(maxsize=None)
def sound(token):
    pointer = c.c_char_p(token.encode('utf-8'))
    ipa = lib.espeak_TextToPhonemes(c.byref(pointer), 1, 2 | (ord('|') << 8)).decode()
    phones = [re.sub(r'[ˈˌ() ]', '', item) for item in re.split(r'[| ]+', ipa) if item.strip()]
    result, onset = [], []
    for index, phone in enumerate(phones):
        if phone not in vowels:
            onset.append(phone)
            continue
        consonant = onset[-1] if onset else ''
        prefix = ''.join(tail.get(item, '') for item in onset[:-1])
        vowel = vowels[phone]
        key = consonant.replace('ɡ', 'g').replace('ɹ', 'r') + 'aeioueaao'[vowel] + ' n'
        closes_syllable = (index+1 < len(phones) and phones[index+1] == 'n' and
                           (index+2 == len(phones) or phones[index+2] not in vowels))
        if closes_syllable and key in joint:
            result.append(prefix + joint[key])
            phones[index+1] = ''
        else:
            result.append(prefix + table.get(consonant, table[''])[vowel])
            if phone in ('əl', 'ən', 'əm'):
                result.append(tail[phone[-1]])
        onset.clear()
    result.append(''.join(tail.get(item, '') for item in onset))
    return ''.join(result).strip() or ''.join(letter.get(char.upper(), '') for char in token) or '未译地名'


COMMON = {
    "anchorage": "安克雷奇", "austin": "奥斯汀", "boston": "波士顿",
    "charlotte": "夏洛特", "chicago": "芝加哥", "columbus": "哥伦布",
    "dallas": "达拉斯", "denver": "丹佛", "detroit": "底特律",
    "fort worth": "沃思堡", "greenwich": "格林尼治", "houston": "休斯敦",
    "indianapolis": "印第安纳波利斯", "jacksonville": "杰克逊维尔",
    "las vegas": "拉斯维加斯", "los angeles": "洛杉矶", "memphis": "孟菲斯",
    "miami": "迈阿密", "milwaukee": "密尔沃基", "minneapolis": "明尼阿波利斯",
    "nashville": "纳什维尔", "new orleans": "新奥尔良", "new york": "纽约",
    "oakland": "奥克兰", "oklahoma city": "俄克拉何马城", "philadelphia": "费城",
    "phoenix": "菲尼克斯", "pittsburgh": "匹兹堡", "portland": "波特兰",
    "sacramento": "萨克拉门托", "salt lake city": "盐湖城", "san antonio": "圣安东尼奥",
    "san diego": "圣迭戈", "san francisco": "旧金山", "san jose": "圣何塞",
    "seattle": "西雅图", "st louis": "圣路易斯", "tucson": "图森",
    "urban honolulu": "檀香山城区", "honolulu": "檀香山", "wichita": "威奇托",
    "arlington": "阿灵顿", "richmond": "里士满", "virginia beach": "弗吉尼亚比奇",
}
CHINESE = re.compile(r"[\u3400-\u9fff·－-]+")
UNIT = re.compile(r"(?:人口普查指定地区|普查指定地区|自治市镇|乡镇|市|镇|村)$")


def normalize(name):
    plain = unicodedata.normalize("NFKD", name.casefold())
    return " ".join(re.findall("[a-z0-9]+", plain.encode("ascii", "ignore").decode()))


def geonames_aliases(path):
    cc = OpenCC("t2s")
    aliases = {}
    with ZipFile(path) as archive, archive.open("US.txt") as records:
        for line in records:
            row = line.decode("utf-8").rstrip("\n").split("\t")
            if row[6] != "P" or len(row[10]) != 2:
                continue
            for alias in row[3].split(","):
                if CHINESE.fullmatch(alias):
                    key = (row[10], normalize(row[1]))
                    population = int(row[14])
                    if key not in aliases or population > aliases[key][0]:
                        aliases[key] = population, UNIT.sub("", cc.convert(alias))
                    break
    return {key: name for key, (_, name) in aliases.items()}


@lru_cache(maxsize=None)
def phonetic(name):
    return "·".join(sound(token) for token in name.split())


def chinese_name(name, abbreviation, aliases, known, suffix):
    key = normalize(name)
    label = COMMON.get(key) or aliases.get((abbreviation, key)) or known.get(key) or phonetic(key)
    return label if label.endswith(suffix) or suffix == "市" and label.endswith("城") else label+suffix
