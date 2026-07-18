"""Authoritative item definitions and two-component recipes."""
BASE_ITEMS = {
    'spices': {'name': '20kg przypraw', 'kind': 'base', 'stats': {'attack': 8}},
    'orangeade': {'name': 'Oranżada helena', 'kind': 'base', 'stats': {'mana_regen': 3, 'max_mana': -10}},
    'coat': {'name': 'Płaszcz 100% wełna', 'kind': 'base', 'stats': {'hp': 120, 'defense': 8}},
    'safe': {'name': 'Mobilny sejf', 'kind': 'base', 'stats': {'hp': 40, 'defense': 20}},
    'socks': {'name': 'Zakolanówki Edyty', 'kind': 'base', 'stats': {'attack_speed': 0.12}},
    'notebook': {'name': 'Notatnik miłości', 'kind': 'base', 'stats': {'hp_regen_per_sec': 2}},
}
_RECIPES = {
 ('spices','orangeade'): ('sugar_rush','Przyprawiona oranżada',{'attack':12,'mana_regen':5},'Pełna mana wzmacnia następny bonusowy atak o 20%.'),
 ('spices','coat'): ('seasoned_armor','Wełniana panierka',{'attack':10,'defense':10},'Pierwszy atak przeciwko właścicielowi zadaje 25% mniej obrażeń.'),
 ('spices','safe'): ('contraband','Przyprawiony sejf',{'attack':14,'defense':6},'Ataki przeciw tarczom zadają 25% więcej obrażeń.'),
 ('spices','socks'): ('hot_feet','Ostre tempo',{'attack':6,'attack_speed':.15},'Bonusowy atak daje 10 many.'),
 ('spices','notebook'): ('recipe_for_love','Przepis na miłość',{'attack':8},'Leczy właściciela za 8% zadanych obrażeń.'),
 ('orangeade','coat'): ('warm_drink','Ciepły kubrak',{'hp':100,'mana_regen':3},'Poniżej 50% HP tworzy tarczę równą 12% maksymalnego HP.'),
 ('orangeade','safe'): ('emergency_reserve','Rezerwa awaryjna',{'hp':70,'max_mana':-5},'Startuje z tarczą równą 15% maksymalnego HP.'),
 ('orangeade','socks'): ('bubbly_steps','Bąbelkowe kroki',{'attack_speed':.2,'mana_regen':2},'Co trzeci atak daje 5 dodatkowej many.'),
 ('orangeade','notebook'): ('sweet_memory','Słodkie wspomnienie',{'mana_regen':6,'hp_regen_per_sec':2},'Otrzymane leczenie daje 10% szybkości ataku na 3 sekundy.'),
 ('coat','safe'): ('fortified_vault','Wełniany bunkier',{'hp':180,'defense':25},'Pierwsze obrażenia w walce są zmniejszone o 50%.'),
 ('coat','socks'): ('woolen_stride','Wełniany sprint',{'hp':80,'attack_speed':.1},'Przy pełnym HP zadaje 12% więcej obrażeń.'),
 ('coat','notebook'): ('love_warmth','Ciepło miłości',{'hp':140,'defense':8},'Regeneracja HP jest zwiększona o 50%.'),
 ('safe','socks'): ('quick_draw','Szybki sejf',{'defense':10,'attack_speed':.2},'Pierwszy atak wybiera cel z najmniejszym HP.'),
 ('safe','notebook'): ('secure_heart','Bezpieczne serce',{'hp':100,'defense':12},'Otrzymywane obrażenia są zmniejszone o 8%.'),
 ('socks','notebook'): ('love_on_the_move','Miłość w ruchu',{'attack_speed':.15,'hp_regen_per_sec':2},'Co piąty atak leczy za 12% zadanych obrażeń.'),
}
ITEMS = dict(BASE_ITEMS)
for (left, right), (item_id, name, stats, description) in _RECIPES.items():
    ITEMS[item_id] = {'name': name, 'kind': 'combined', 'components': [left, right], 'stats': stats, 'description': description}
RECIPES = {tuple(sorted(pair)): value[0] for pair, value in _RECIPES.items()}
def item_payload(item_id):
    return {'id': item_id, **ITEMS[item_id]}
def all_item_payloads():
    return [item_payload(item_id) for item_id in ITEMS]
def combine_item_ids(first, second):
    return RECIPES.get(tuple(sorted((first, second))))
