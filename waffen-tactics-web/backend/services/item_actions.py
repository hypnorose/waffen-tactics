from waffen_tactics.services.items import BASE_ITEMS, ITEMS, combine_item_ids

def _find_unit(player, instance_id):
    return next((u for u in player.board + player.bench if u.instance_id == instance_id), None)

def equip_item(player, instance_id, item_id):
    if not isinstance(item_id, str) or item_id not in ITEMS:
        return False, 'Nieznany przedmiot'
    unit = _find_unit(player, instance_id)
    if not unit:
        return False, 'Nie znaleziono jednostki'
    if item_id not in player.item_inventory:
        return False, 'Nie posiadasz tego przedmiotu'

    # The approved WFT-139 matrix is the only source of auto-combine rules.
    # Keep slot order deterministic when more than one base-item partner is
    # already equipped; the first compatible slot is replaced by the result.
    partner_index = None
    combined_id = None
    if item_id in BASE_ITEMS:
        for index, equipped_id in enumerate(unit.items):
            if not isinstance(equipped_id, str) or equipped_id not in BASE_ITEMS:
                continue
            candidate = combine_item_ids(item_id, equipped_id)
            if candidate:
                partner_index = index
                combined_id = candidate
                break

    if combined_id is not None and partner_index is not None:
        player.item_inventory.remove(item_id)
        unit.items[partner_index] = combined_id
        return True, f"Połączono i założono: {ITEMS[combined_id]['name']}"

    if len(unit.items) >= 3:
        return False, 'Jednostka ma już 3 przedmioty'

    player.item_inventory.remove(item_id)
    unit.items.append(item_id)
    return True, f"Założono: {ITEMS[item_id]['name']}"

def combine_item(player, first, second):
    if first not in player.item_inventory or second not in player.item_inventory:
        return False, 'Potrzebujesz dwóch przedmiotów bazowych'
    if first == second and player.item_inventory.count(first) < 2:
        return False, 'Potrzebujesz dwóch przedmiotów bazowych'
    result = combine_item_ids(first, second)
    if not result:
        return False, 'Te przedmioty nie mają receptury'
    player.item_inventory.remove(first)
    player.item_inventory.remove(second)
    player.item_inventory.append(result)
    return True, f"Połączono w: {ITEMS[result]['name']}"
