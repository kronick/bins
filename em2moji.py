#coding=utf-8

emoji_string = u"🏠💦🌺🍆💰🍕🍺😈🐣😻️🐳💯🌚💾🌵🎈😎💩❤️😢👗💕💊🔫🎉🎶👌🙌😀😂👀🙈😘😨⚡️✋✌️🙏💁👯🚶🚴🏄🗻🌍👶👍🏢☔️🐝🍌💸🍔🍻👿🐥😹🐘🎯🌞💽🌴🌹😉💎💔😭👕💖💉💥💃✨🆗👐😆😜👅🙉😍😱🔥👋🖖👏🙅👭🏃🏇🌐🌋🔮👵👎🏫🐬🌸🍉💳🍴🍸👻🐔🙀🐍🔔😴💻🌿💄⛄️🚽💜😠👙💘😝💣🎊🎹✔️💪😌😅👂🐒💋😲✏️💅✊🙇🙋👫👦🚂🏂🌌🎱👼☝️🏰🐙🌷🍡👹🍩🍯🐉🐧🐱🐞🏆🐸📺🍃🗼❄️🐂💛😤👟🐾🌟😲🎅🎸⭐️✳️😏😛👓🍌💐😷🔨🚫‼️💭💆👥👨🚅☁️🌉🆘⌛️🎨⛺️🌊🌻🌽💱🍟🍷👺🐓😿🐖🎲👽📲🌲📕🆒🇺🇸💙😫👖💞🍄🔪🎁🎧👈👉☺️😁👃🙊😚😳💡🙅👊👇🙆👬👧🚌🏊🌈⚽️👴👆🌇🐟🐛🍑👑🍦☕️👾🍗😺🐢🏁👤📷🌾🚩😇🍀💚😡👠💗🌀🚬🎀🎷➕↔️😊😋👄🐵💌😔🔦🔙♊️🎆💇🎭👩🚜🌁🎪🏀💀⭐️".encode("utf8")
emoji_map = []
chars = 10000;

def utf8_lead_byte(b):
    '''A UTF-8 intermediate byte starts with the bits 10xxxxxx.'''
    return (ord(b) & 0xC0) != 0x80

# Split the emoji_string into a map of individual characters
char_start = 0
for b in range(len(emoji_string)):
    if utf8_lead_byte(emoji_string[b]) and b > 0:
        # Add buffer to emoji_map and reset
        emoji_map.append(emoji_string[char_start:b])
        char_start = b


def get_emoji(uuid):
    out = u""

    uuid = uuid.replace("-","")
    print uuid
    for i in range(0, len(uuid), 2):
        out += unicode(emoji_map[int(uuid[i:i+1], 16)], "utf-8")
        #out += u"😎"
    return out