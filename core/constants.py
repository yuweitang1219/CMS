# core/constants.py

LTC_SERVICES = [
    # BA
    {'code': 'BA01', 'desc': '基本身體清潔', 'price': 260, 'type': 'BC'},
    {'code': 'BA02', 'desc': '基本日常照顧', 'price': 195, 'type': 'BC'},
    {'code': 'BA03', 'desc': '測量生命徵象', 'price': 35, 'type': 'BC'},
    {'code': 'BA04', 'desc': '協助進食或管灌餵食', 'price': 130, 'type': 'BC'},
    {'code': 'BA05', 'desc': '餐食照顧', 'price': 310, 'type': 'BC'},
    {'code': 'BA07', 'desc': '協助沐浴及洗頭', 'price': 325, 'type': 'BC'},
    {'code': 'BA08', 'desc': '足部照護', 'price': 500, 'type': 'BC'},
    {'code': 'BA09', 'desc': '到宅沐浴車-第一型', 'price': 2200, 'type': 'BC'},
    {'code': 'BA09a', 'desc': '到宅沐浴車-第二型', 'price': 2500, 'type': 'BC'},
    {'code': 'BA10', 'desc': '翻身拍背', 'price': 155, 'type': 'BC'},
    {'code': 'BA11', 'desc': '肢體關節活動', 'price': 195, 'type': 'BC'},
    {'code': 'BA12', 'desc': '協助上下樓梯', 'price': 130, 'type': 'BC'},
    {'code': 'BA13', 'desc': '陪同外出', 'price': 195, 'type': 'BC'},
    {'code': 'BA14', 'desc': '陪同就醫', 'price': 685, 'type': 'BC'},
    {'code': 'BA15', 'desc': '家務協助', 'price': 195, 'type': 'BC'},
    {'code': 'BA16', 'desc': '代購或代領或代送服務', 'price': 130, 'type': 'BC'},
    {'code': 'BA17a', 'desc': '人工氣道管內抽吸', 'price': 75, 'type': 'BC'},
    {'code': 'BA17b', 'desc': '口腔內分泌物抽吸', 'price': 65, 'type': 'BC'},
    {'code': 'BA17c', 'desc': '尿管及鼻胃管之清潔與固定', 'price': 50, 'type': 'BC'},
    {'code': 'BA17d1', 'desc': '攜帶式血糖機驗血糖', 'price': 50, 'type': 'BC'},
    {'code': 'BA17d2', 'desc': '甘油球通便', 'price': 50, 'type': 'BC'},
    {'code': 'BA17e', 'desc': '依指示置入藥盒', 'price': 50, 'type': 'BC'},
    {'code': 'BA18', 'desc': '安全看視', 'price': 200, 'type': 'BC'},
    {'code': 'BA20', 'desc': '陪伴服務', 'price': 175, 'type': 'BC'},
    {'code': 'BA22', 'desc': '巡視服務', 'price': 130, 'type': 'BC'},
    {'code': 'BA23', 'desc': '協助洗頭', 'price': 200, 'type': 'BC'},
    {'code': 'BA24', 'desc': '協助排泄', 'price': 220, 'type': 'BC'},

    # BB (日間照顧)
    {'code': 'BB01', 'desc': '日間照顧(全日)-第2級', 'price': 675, 'type': 'BC'},
    {'code': 'BB02', 'desc': '日間照顧(半日)-第2級', 'price': 340, 'type': 'BC'},
    {'code': 'BB03', 'desc': '日間照顧(全日)-第3級', 'price': 750, 'type': 'BC'},
    {'code': 'BB04', 'desc': '日間照顧(半日)-第3級', 'price': 375, 'type': 'BC'},
    {'code': 'BB05', 'desc': '日間照顧(全日)-第4級', 'price': 835, 'type': 'BC'},
    {'code': 'BB06', 'desc': '日間照顧(半日)-第4級', 'price': 420, 'type': 'BC'},
    {'code': 'BB07', 'desc': '日間照顧(全日)-第5級', 'price': 925, 'type': 'BC'},
    {'code': 'BB08', 'desc': '日間照顧(半日)-第5級', 'price': 465, 'type': 'BC'},
    {'code': 'BB09', 'desc': '日間照顧(全日)-第6級', 'price': 1020, 'type': 'BC'},
    {'code': 'BB10', 'desc': '日間照顧(半日)-第6級', 'price': 510, 'type': 'BC'},
    {'code': 'BB11', 'desc': '日間照顧(全日)-第7級', 'price': 1115, 'type': 'BC'},
    {'code': 'BB12', 'desc': '日間照顧(半日)-第7級', 'price': 560, 'type': 'BC'},
    {'code': 'BB13', 'desc': '日間照顧(全日)-第8級', 'price': 1215, 'type': 'BC'},
    {'code': 'BB14', 'desc': '日間照顧(半日)-第8級', 'price': 610, 'type': 'BC'},

    # BC (家庭托顧)
    {'code': 'BC01', 'desc': '家庭托顧(全日)-第2級', 'price': 760, 'type': 'BC'},
    {'code': 'BC02', 'desc': '家庭托顧(半日)-第2級', 'price': 380, 'type': 'BC'},
    {'code': 'BC03', 'desc': '家庭托顧(全日)-第3級', 'price': 820, 'type': 'BC'},
    {'code': 'BC04', 'desc': '家庭托顧(半日)-第3級', 'price': 410, 'type': 'BC'},
    {'code': 'BC05', 'desc': '家庭托顧(全日)-第4級', 'price': 890, 'type': 'BC'},
    {'code': 'BC06', 'desc': '家庭托顧(半日)-第4級', 'price': 445, 'type': 'BC'},
    {'code': 'BC07', 'desc': '家庭托顧(全日)-第5級', 'price': 970, 'type': 'BC'},
    {'code': 'BC08', 'desc': '家庭托顧(半日)-第5級', 'price': 485, 'type': 'BC'},
    {'code': 'BC09', 'desc': '家庭托顧(全日)-第6級', 'price': 1030, 'type': 'BC'},
    {'code': 'BC10', 'desc': '家庭托顧(半日)-第6級', 'price': 515, 'type': 'BC'},
    {'code': 'BC11', 'desc': '家庭托顧(全日)-第7級', 'price': 1110, 'type': 'BC'},
    {'code': 'BC12', 'desc': '家庭托顧(半日)-第7級', 'price': 555, 'type': 'BC'},
    {'code': 'BC13', 'desc': '家庭托顧(全日)-第8級', 'price': 1180, 'type': 'BC'},
    {'code': 'BC14', 'desc': '家庭托顧(半日)-第8級', 'price': 590, 'type': 'BC'},

    # BD (小規模多機能)
    {'code': 'BD01', 'desc': '小規模多機能(全日)-第2級', 'price': 760, 'type': 'BC'},
    {'code': 'BD02', 'desc': '小規模多機能(半日)-第2級', 'price': 380, 'type': 'BC'},
    {'code': 'BD03', 'desc': '小規模多機能(全日)-第3級', 'price': 820, 'type': 'BC'},
    {'code': 'BD04', 'desc': '小規模多機能(半日)-第3級', 'price': 410, 'type': 'BC'},
    {'code': 'BD05', 'desc': '小規模多機能(全日)-第4級', 'price': 890, 'type': 'BC'},
    {'code': 'BD06', 'desc': '小規模多機能(半日)-第4級', 'price': 445, 'type': 'BC'},
    {'code': 'BD07', 'desc': '小規模多機能(全日)-第5級', 'price': 970, 'type': 'BC'},
    {'code': 'BD08', 'desc': '小規模多機能(半日)-第5級', 'price': 485, 'type': 'BC'},
    {'code': 'BD09', 'desc': '小規模多機能(全日)-第6級', 'price': 1030, 'type': 'BC'},
    {'code': 'BD10', 'desc': '小規模多機能(半日)-第6級', 'price': 515, 'type': 'BC'},
    {'code': 'BD11', 'desc': '小規模多機能(全日)-第7級', 'price': 1110, 'type': 'BC'},
    {'code': 'BD12', 'desc': '小規模多機能(半日)-第7級', 'price': 555, 'type': 'BC'},
    {'code': 'BD13', 'desc': '小規模多機能(全日)-第8級', 'price': 1180, 'type': 'BC'},
    {'code': 'BD14', 'desc': '小規模多機能(半日)-第8級', 'price': 590, 'type': 'BC'},

    # C
    {'code': 'CA01', 'desc': '復能照護(居家)', 'price': 1500, 'type': 'BC'},
    {'code': 'CA02', 'desc': '復能照護(社區)', 'price': 1500, 'type': 'BC'},
    {'code': 'CA03', 'desc': '復能照護(機構)', 'price': 1500, 'type': 'BC'},
    {'code': 'CA04', 'desc': '復能照護(小作所)', 'price': 1500, 'type': 'BC'},
    {'code': 'CA07', 'desc': 'IADLs復能、ADLs復能照護', 'price': 4500, 'type': 'BC'},
    {'code': 'CA08', 'desc': '個別化服務計畫(ISP)', 'price': 6000, 'type': 'BC'},
    {'code': 'CB01', 'desc': '營養照護', 'price': 4000, 'type': 'BC'},
    {'code': 'CB02', 'desc': '進食與吞嚥照護', 'price': 9000, 'type': 'BC'},
    {'code': 'CB03', 'desc': '困擾行為照護', 'price': 4500, 'type': 'BC'},
    {'code': 'CB04', 'desc': '臥床或長期活動受限照護', 'price': 9000, 'type': 'BC'},
    {'code': 'CC01', 'desc': '居家環境安全或無障礙空間規劃', 'price': 2000, 'type': 'BC'},
    {'code': 'CD02', 'desc': '居家護理指導與諮詢', 'price': 6000, 'type': 'BC'},
    {'code': 'CE01', 'desc': '社區長照機構護理指導', 'price': 1500, 'type': 'BC'},
    {'code': 'CG01', 'desc': '管路清潔與耗材更換', 'price': 1500, 'type': 'BC'},
    {'code': 'CG02', 'desc': '個別化護理衛教', 'price': 1000, 'type': 'BC'},

    # D
    {'code': 'DA01', 'desc': '交通接送(依地區計價)', 'price': 100, 'type': 'D'},

    # EF
    {'code': 'EA01', 'desc': '馬桶增高器或沐浴椅', 'price': 1200, 'type': 'EF'},
    {'code': 'EA02', 'desc': '便盆椅', 'price': 3000, 'type': 'EF'},
    {'code': 'EA03', 'desc': '沐浴床', 'price': 6000, 'type': 'EF', 'evalReq': True},
    {'code': 'EB01', 'desc': '單支枴杖', 'price': 1000, 'type': 'EF'},
    {'code': 'EB03', 'desc': '助行器', 'price': 800, 'type': 'EF'},
    {'code': 'EB04', 'desc': '帶輪型助步車', 'price': 3000, 'type': 'EF', 'evalReq': True},
    {'code': 'EB05', 'desc': '四腳拐', 'price': 500, 'type': 'EF'},
    {'code': 'EB06', 'desc': '前臂拐', 'price': 2000, 'type': 'EF'},
    {'code': 'EC01', 'desc': '輪椅-A款', 'price': 3000, 'type': 'EF'},
    {'code': 'EC02', 'desc': '輪椅-B款', 'price': 4000, 'type': 'EF', 'evalReq': True},
    {'code': 'EC03', 'desc': '輪椅-C款(附加功能)', 'price': 6000, 'type': 'EF', 'evalReq': True},
    {'code': 'ED01', 'desc': '移位機', 'price': 10000, 'type': 'EF', 'evalReq': True},
    {'code': 'ED02', 'desc': '移位滑墊', 'price': 2000, 'type': 'EF', 'evalReq': True},
    {'code': 'EG01', 'desc': '氣墊床-A款', 'price': 8000, 'type': 'EF', 'evalReq': True},
    {'code': 'EG02', 'desc': '氣墊床-B款', 'price': 12000, 'type': 'EF', 'evalReq': True},
    {'code': 'EH01', 'desc': '居家用照顧床', 'price': 8000, 'type': 'EF', 'evalReq': True},
    {'code': 'EH02', 'desc': '電動照顧床附加功能', 'price': 15000, 'type': 'EF', 'evalReq': True},
    {'code': 'FA03', 'desc': '非固定式斜坡板-A款', 'price': 3500, 'type': 'EF', 'evalReq': True},
    {'code': 'FA04', 'desc': '非固定式斜坡板-B款', 'price': 5000, 'type': 'EF', 'evalReq': True},
    {'code': 'FA05', 'desc': '非固定式斜坡板-C款', 'price': 7000, 'type': 'EF', 'evalReq': True},
    {'code': 'FA18', 'desc': '流理台改善', 'price': 15000, 'type': 'EF', 'evalReq': True},

    # G
    {'code': 'GA01', 'desc': '居家喘息服務(半日)', 'price': 770, 'type': 'G'},
    {'code': 'GA02', 'desc': '居家喘息服務(全日)', 'price': 1540, 'type': 'G'},
    {'code': 'GA03', 'desc': '日照中心喘息(全日)', 'price': 1250, 'type': 'G'},
    {'code': 'GA04', 'desc': '日照中心喘息(半日)', 'price': 625, 'type': 'G'},
    {'code': 'GA05', 'desc': '機構住宿式喘息(全日)', 'price': 2310, 'type': 'G'},
    {'code': 'GA06', 'desc': '小機夜間喘息', 'price': 2000, 'type': 'G'},
    {'code': 'GA07', 'desc': '巷弄長照站喘息(每小時)', 'price': 170, 'type': 'G'},
    {'code': 'GA09', 'desc': '居家喘息服務(每2小時)', 'price': 770, 'type': 'G'},

    # SC
    {'code': 'SC09', 'desc': '短期替代照顧服務', 'price': 770, 'type': 'SC'},

    # Z
    {'code': 'ZH01', 'desc': '緊急救援服務', 'price': 1200, 'type': 'Z'},

    # OT
    {'code': 'OT', 'desc': '營養送餐', 'price': 0, 'type': 'OT'}
]


COPAY_RATES = {
    'BC': [0.16, 0.05, 0],
    'D': [0.21, 0.07, 0],
    'G': [0.16, 0.05, 0],
    'EF': [0.3, 0.1, 0],
    'SC': [0.16, 0.05, 0],
    'Z': [1, 1, 1],
    'OT': [1, 1, 1]
}

PROBLEM_LIST = [
    {'id': 'p1', 'name': '1-備餐問題', 'baCode': 'BA05', 'baDesc': '餐食照顧', 'text': '核定[BA05餐食照顧]，協助準備午餐，提供每日營養所需。', 'options': ['核定[BA05餐食照顧]', '提供每日營養所需', '其他']},
    {'id': 'p2', 'name': '2-洗澡問題', 'baCode': 'BA07', 'baDesc': '協助沐浴及洗頭', 'text': '核定[BA07協助沐浴及洗頭]，協助個案身體清潔。', 'options': ['協助沐浴及洗頭', '協助個案身體清潔', '其他']},
    {'id': 'p3', 'name': '3-穿脫衣物問題', 'baCode': 'BA02', 'baDesc': '基本日常照顧', 'text': '核定[BA02基本日常照顧]，協助個案清潔便盆、大小便後清潔及移位。', 'options': ['服務核定', '協助穿換衣服', '其他']},
    {'id': 'p4', 'name': '4-個人修飾問題', 'baCode': 'BA02', 'baDesc': '基本日常照顧', 'text': '核定[BA02基本日常照顧]，協助個案清潔便盆、大小便後清潔及移位。', 'options': ['服務核定', '個體清潔', '其他']},
    {'id': 'p5', 'name': '5-處理家務問題', 'baCode': 'BA15', 'baDesc': '家務服務', 'text': '核定[BA15家務服務]，整理臥室床鋪及地板清潔。', 'options': ['協助換洗', '整理環境', '其他']},
    {'id': 'p6', 'name': '6-進食問題', 'baCode': 'BA04', 'baDesc': '協助進食或管灌餵食', 'text': '核定[BA04協助進食或管灌餵食]，協助加熱晚餐。', 'options': ['協助加熱', '管灌餵食', '其他']},
    {'id': 'p7', 'name': '7-照顧負荷過重專區', 'baCode': 'GA09', 'baDesc': '喘息服務', 'text': '[GA09喘息服務]，提供替代照顧減輕負擔。', 'options': ['服務提供', '減輕負擔', '其他']},
    {'id': 'p8', 'name': '8-大小便控制問題', 'baCode': 'BA02', 'baDesc': '基本日常照顧', 'text': '核定[BA02基本日常照顧]，協助個案清潔便盆、大小便後清潔及移位。', 'options': ['服務核定', '清理便盆', '其他']},
    {'id': 'p9', 'name': '9-翻身拍背問題', 'baCode': 'BA10', 'baDesc': '翻身拍背', 'text': '核定[BA10翻身拍背]，協助翻身拍背，預防壓瘡。', 'options': ['協助翻身拍背', '預防壓瘡', '其他']},
    {'id': 'p10', 'name': '10-肢體關節活動問題', 'baCode': 'BA11', 'baDesc': '肢體關節活動', 'text': '核定[BA11肢體關節活動]，協助關節活動，維持關節靈活。', 'options': ['協助關節活動', '預防攣縮', '其他']},
    {'id': 'p11', 'name': '11-協助上下樓梯問題', 'baCode': 'BA12', 'baDesc': '協助上下樓梯', 'text': '核定[BA12協助上下樓梯]，協助上下樓梯移動安全。', 'options': ['協助移動', '維護安全', '其他']},
    {'id': 'p12', 'name': '12-陪同外出問題', 'baCode': 'BA13', 'baDesc': '陪同外出', 'text': '核定[BA13陪同外出]，陪伴外出散步舒心。', 'options': ['陪伴外出', '心理支持', '其他']},
    {'id': 'p13', 'name': '13-陪同就醫問題', 'baCode': 'BA14', 'baDesc': '陪同就醫', 'text': '核定[BA14陪同就醫]，陪伴就醫診治。', 'options': ['陪伴就醫', '協助診療', '其他']},
    {'id': 'p14', 'name': '14-足部照護問題', 'baCode': 'BA08', 'baDesc': '足部照護', 'text': '核定[BA08足部照護]，清剪趾甲預防甲溝炎。', 'options': ['足部清潔', '清剪趾甲', '其他']},
    {'id': 'p15', 'name': '15-協助洗頭問題', 'baCode': 'BA23', 'baDesc': '協助洗頭', 'text': '核定[BA23協助洗頭]，保持頭髮清潔舒適。', 'options': ['協助洗頭', '清潔舒適', '其他']},
    {'id': 'p16', 'name': '16-安全看視/陪伴問題', 'baCode': 'BA18', 'baDesc': '安全看視/陪伴', 'text': '核定[BA18安全看視]，維護居家安全防止意外。', 'options': ['安全看視', '防止意外', '其他']},
    {'id': 'p17', 'name': '17. 其他需求', 'options': ['轉介資源', '心理支持', '其他']}
]

KEYWORD_SERVICE_MAP = {
    '洗澡': ['BA07', 'BA09', 'BA09a', 'EA01'], '沐浴': ['BA07', 'BA09', 'BA09a', 'EA01'],
    '陪伴': ['BA20'], '散步': ['BA20', 'BA13'], '看視': ['BA18', 'BA22'],
    '就醫': ['BA14', 'DA01'], '回診': ['BA14', 'DA01'], '門診': ['BA14', 'DA01'],
    '拿藥': ['BA16'], '代購': ['BA16'], '買': ['BA16'],
    '備餐': ['BA05'], '煮飯': ['BA05'], '煮菜': ['BA05'],
    '送餐': ['OT'], '便當': ['OT'], '餐飲': ['OT'],
    '管灌': ['BA04'], '餵食': ['BA04'], '進食': ['BA04'],
    '抽痰': ['BA17a', 'BA17b'], '鼻胃管': ['BA17c'], '尿管': ['BA17c'],
    '甘油球': ['BA17d2'], '血糖': ['BA17d1'], '用藥': ['BA17e'],
    '復健': ['CA07', 'CA01'], '復能': ['CA07'], '關節': ['BA11'], '中風': ['CA07', 'BA11'],
    '翻身': ['BA10'], '拍背': ['BA10'],
    '打掃': ['BA15'], '家務': ['BA15'], '整理': ['BA15'], '洗衣服': ['BA15'], '洗衣': ['BA15'],
    '洗頭': ['BA23', 'BA07'], '足部': ['BA08'], '剪指甲': ['BA08'],
    '排泄': ['BA24', 'BA02'], '尿布': ['BA24'], '廁所': ['BA24', 'BA02'], '便盆': ['EA02'],
    '外出': ['BA13', 'DA01'],
    '喘息': ['GA09', 'GA01', 'GA02'], '短照': ['SC09'],
    '輪椅': ['EC01', 'EC02', 'EC03'], '助行器': ['EB03', 'EB04'], '拐杖': ['EB01', 'EB05'], '枴杖': ['EB01', 'EB05'],
    '氣墊床': ['EG01', 'EG02'], '照顧床': ['EH01', 'EH01'], '電動床': ['EH01', 'EH02'],
    '洗澡椅': ['EA01'], '扶手': ['CC01'], '防滑': ['CC01'], '無障礙': ['CC01']
}

CMS_QUOTA_MAP = {2: 10020, 3: 15460, 4: 18580, 5: 24100, 6: 28070, 7: 32090, 8: 36180}
TRAFFIC_QUOTA_MAP = {1: 1680, 2: 1840, 3: 2000, 4: 2400}
RESPITE_QUOTA_MAP = {2: 32340, 3: 32340, 4: 32340, 5: 32340, 6: 32340, 7: 48510, 8: 48510}
EF_QUOTA = 40000

CONDITIONS_LIST = ['高血壓', '糖尿病', '心臟病', '腦中風', '失智症', '關節炎', '巴金森氏症', '其他']
SENSORY_LIST = ['視力模糊', '白內障', '聽力退化', '重聽', '表達困難', '理解困難', '其他']
TUBES_LIST = ['無', '鼻胃管', '導尿管', '氣切管', '胃造口', '腸造口', '其他']
COGNITION_LIST = ['無明顯異常', '確診失智症', '疑似失智/CDR異常', '睡眠障礙/日夜顛倒', '遊走/走失風險', '幻覺/妄想', '其他']
FALLS_LIST = ['無', '過去一年內曾跌倒1次', '過去一年內曾跌倒2次以上', '其他']
ADL_LIST = ['進食', '洗澡', '個人修飾', '穿脫衣物', '大便控制', '小便控制', '如廁', '床椅移位', '平地走動', '上下樓梯']
IADL_LIST = ['上街購物', '外出搭車', '食物烹調', '家務維持', '洗衣服', '使用電話', '服用藥物', '處理財務']
INCOME_LIST = [
    '案子提供', '案女提供', '配偶提供', '其他家屬提供',
    '中低收老人生活津貼', '身心障礙生活補助', '老農津貼', '原住民給付', '榮民就養給付',
    '國民年金', '勞保老年給付/勞退', '軍公教退休金',
    '個人儲蓄/存款', '租金/投資收益', '工作薪資', '其他'
]
