from waffen_tactics.services.items import ITEMS, combine_item_ids

def _find_unit(player, instance_id):
    return next((u for u in player.board + player.bench if u.instance_id == instance_id), None)

def equip_item(player, instance_id, item_id):
    if item_id not in ITEMS:
        return False, 'Nieznany przedmiot'
    unit = _find_unit(player, instance_id)
    if not unit:
        return False, 'Nie znaleziono jednostki'
    if len(unit.items) >= 3:
        return False, 'Jednostka ma już 3 przedmioty'
    if item_id not in player.item_inventory:
        return False, 'Nie posiadasz tego przedmiotu'
    player.item_inventory.remove(item_id)
    unit.items.append(item_id)
    return True, f"Założono: {ITEMS[item_id]['name']}"

def combine_item(player, first, second):
    if first == second or first not in player.item_inventory or second not in player.item_inventory:
        return False, 'Potrzebujesz dwóch różnych przedmiotów bazowych'
    result = combine_item_ids(first, second)
    if not result:
        return False, 'Te przedmioty nie mają receptury'
    player.item_inventory.remove(first)
    player.item_inventory.remove(second)
    player.item_inventory.append(result)
    return True, f"Połączono w: {ITEMS[result]['name']}"
