"""Automatic text commentary in English, Marathi and Hindi.

Commentary is generated only from what the scorer recorded. Shot direction is
mentioned only when the scorer selected a shot zone; nothing else (shot type,
fielding position, crowd reaction) is invented.
"""

LANGUAGES = ("en", "mr", "hi")

ZONES = {
    "en": {
        "fine_leg": "fine leg", "square_leg": "square leg", "mid_wicket": "mid-wicket", "mid_on": "mid-on",
        "straight": "down the ground", "mid_off": "mid-off", "cover": "the covers", "point": "point",
        "third_man": "third man",
    },
    "mr": {
        "fine_leg": "फाइन लेग", "square_leg": "स्क्वेअर लेग", "mid_wicket": "मिड-विकेट", "mid_on": "मिड-ऑन",
        "straight": "सरळ", "mid_off": "मिड-ऑफ", "cover": "कव्हर्स", "point": "पॉइंट", "third_man": "थर्ड मॅन",
    },
    "hi": {
        "fine_leg": "फाइन लेग", "square_leg": "स्क्वेयर लेग", "mid_wicket": "मिड-विकेट", "mid_on": "मिड-ऑन",
        "straight": "सीधे", "mid_off": "मिड-ऑफ", "cover": "कवर्स", "point": "पॉइंट", "third_man": "थर्ड मैन",
    },
}

DISMISSALS = {
    "en": {
        "bowled": "bowled", "caught": "caught by {fielder}", "caught_and_bowled": "caught and bowled",
        "lbw": "leg before wicket", "run_out": "run out", "stumped": "stumped by {fielder}",
        "hit_wicket": "hit wicket", "obstructing_field": "out for obstructing the field",
        "hit_ball_twice": "out for hitting the ball twice", "timed_out": "timed out",
        "retired_out": "retired out", "retired_hurt": "retired hurt",
    },
    "mr": {
        "bowled": "त्रिफळाचीत", "caught": "{fielder} कडून झेलबाद", "caught_and_bowled": "गोलंदाजाकडूनच झेलबाद",
        "lbw": "पायचीत (LBW)", "run_out": "धावबाद", "stumped": "{fielder} कडून यष्टिचीत",
        "hit_wicket": "हिट विकेट", "obstructing_field": "क्षेत्ररक्षणात अडथळा आणल्याने बाद",
        "hit_ball_twice": "चेंडू दोनदा मारल्याने बाद", "timed_out": "टाइम्ड आउट",
        "retired_out": "रिटायर्ड आउट", "retired_hurt": "दुखापतीमुळे निवृत्त",
    },
    "hi": {
        "bowled": "बोल्ड", "caught": "{fielder} द्वारा कैच आउट", "caught_and_bowled": "कॉट एंड बोल्ड",
        "lbw": "एलबीडब्ल्यू", "run_out": "रन आउट", "stumped": "{fielder} द्वारा स्टंप आउट",
        "hit_wicket": "हिट विकेट", "obstructing_field": "फील्ड में बाधा डालने पर आउट",
        "hit_ball_twice": "गेंद को दो बार मारने पर आउट", "timed_out": "टाइम्ड आउट",
        "retired_out": "रिटायर्ड आउट", "retired_hurt": "रिटायर्ड हर्ट",
    },
}

T = {
    "en": {
        "four": ["FOUR! {batter} finds the boundary{zone}.", "FOUR! {batter} hits it to the rope{zone}."],
        "six": ["SIX! {batter} clears the boundary{zone}!", "SIX! {batter} sends it over the rope{zone}!"],
        "dot": ["No run. {bowler} to {batter}, dot ball.", "{bowler} to {batter}, no run."],
        "runs": ["{bowler} to {batter}, {runs} {run_word}{zone}."],
        "wide": ["Wide from {bowler}. {extra} {run_word} added."],
        "noball": ["No-ball from {bowler}! {extra} {run_word} from it.{free_hit}"],
        "bye": ["{runs} {bye_word}. The ball goes past {batter}."],
        "legbye": ["{runs} leg {bye_word} off {batter}'s body."],
        "penalty": ["{runs} penalty runs awarded to the batting side."],
        "wicket": ["WICKET! {player_out} is {how}. {bowler} strikes!", "OUT! {player_out} {how}."],
        "wicket_runout": ["WICKET! {player_out} is run out{fielder_by}."],
        "free_hit": [" Free hit coming up."],
        "run": "run", "runs_word": "runs", "bye": "bye", "byes": "byes",
        "zone": " through {zone}", "fielder_by": " by {fielder}",
        "over_end": "End of over {over}: {runs} {run_word} from it. Score {score}.",
    },
    "mr": {
        "four": ["चौकार! {batter} चा सुंदर फटका{zone}.", "चौकार! {batter} ने चेंडू सीमारेषेपार पाठवला{zone}."],
        "six": ["षटकार! {batter} चा जबरदस्त षटकार{zone}!", "षटकार! {batter} ने चेंडू थेट प्रेक्षकांत पाठवला{zone}!"],
        "dot": ["एकही धाव नाही. {bowler} विरुद्ध {batter}, निर्धाव चेंडू.", "{bowler} चा चेंडू, {batter} ला धाव नाही."],
        "runs": ["{bowler} विरुद्ध {batter}, {runs} {run_word}{zone}."],
        "wide": ["{bowler} चा वाइड चेंडू. {extra} {run_word} मिळाल्या."],
        "noball": ["{bowler} चा नो-बॉल! त्यातून {extra} {run_word}.{free_hit}"],
        "bye": ["{runs} {bye_word}. चेंडू {batter} ला चकवून गेला."],
        "legbye": ["{batter} च्या पॅडवरून {runs} लेग {bye_word}."],
        "penalty": ["फलंदाजी करणाऱ्या संघाला {runs} दंड धावा."],
        "wicket": ["विकेट! {player_out} {how}. {bowler} ला यश!", "बाद! {player_out} {how}."],
        "wicket_runout": ["विकेट! {player_out} धावबाद{fielder_by}."],
        "free_hit": [" पुढचा चेंडू फ्री हिट."],
        "run": "धाव", "runs_word": "धावा", "bye": "बाय", "byes": "बाय",
        "zone": " ({zone} च्या दिशेने)", "fielder_by": " ({fielder})",
        "over_end": "षटक {over} संपले: {runs} {run_word}. धावसंख्या {score}.",
    },
    "hi": {
        "four": ["चौका! {batter} ने गेंद को सीमा रेखा के पार भेजा{zone}।", "चौका! {batter} का शानदार शॉट{zone}।"],
        "six": ["छक्का! {batter} का गगनचुंबी छक्का{zone}!", "छक्का! {batter} ने गेंद को सीमा के बाहर भेज दिया{zone}!"],
        "dot": ["कोई रन नहीं। {bowler} की गेंद पर {batter} डॉट बॉल।", "{bowler} की गेंद, {batter} कोई रन नहीं ले सके।"],
        "runs": ["{bowler} की गेंद पर {batter}, {runs} {run_word}{zone}।"],
        "wide": ["{bowler} की वाइड गेंद। {extra} {run_word} जुड़े।"],
        "noball": ["{bowler} की नो-बॉल! इससे {extra} {run_word}।{free_hit}"],
        "bye": ["{runs} {bye_word}। गेंद {batter} को छकाकर निकल गई।"],
        "legbye": ["{batter} के पैड से {runs} लेग {bye_word}।"],
        "penalty": ["बल्लेबाज़ी टीम को {runs} पेनल्टी रन मिले।"],
        "wicket": ["विकेट! {player_out} {how}। {bowler} को सफलता!", "आउट! {player_out} {how}।"],
        "wicket_runout": ["विकेट! {player_out} रन आउट{fielder_by}।"],
        "free_hit": [" अगली गेंद फ्री हिट।"],
        "run": "रन", "runs_word": "रन", "bye": "बाय", "byes": "बाय",
        "zone": " ({zone} की दिशा में)", "fielder_by": " ({fielder})",
        "over_end": "ओवर {over} समाप्त: {runs} {run_word}। स्कोर {score}।",
    },
}


def _pick(options, seed):
    return options[seed % len(options)]


def delivery_commentary(lang, *, seed, batter, bowler, runs_bat, wides, noballs, byes, legbyes, penalty_runs,
                        is_boundary, is_penalty_only, shot_zone="", wicket_kind=None, player_out=None,
                        fielder=None, next_is_free_hit=False, wide_runs=1):
    lang = lang if lang in T else "en"
    t = T[lang]

    def run_word(n):
        return t["run"] if n == 1 else t["runs_word"]

    zone = t["zone"].format(zone=ZONES[lang][shot_zone]) if shot_zone in ZONES[lang] else ""
    ctx = {"batter": batter, "bowler": bowler, "zone": zone}
    parts = []
    if is_penalty_only:
        parts.append(_pick(t["penalty"], seed).format(runs=penalty_runs))
    elif wides:
        parts.append(_pick(t["wide"], seed).format(extra=wides, run_word=run_word(wides), **ctx))
    elif noballs:
        extra = noballs + runs_bat + byes + legbyes
        fh = _pick(t["free_hit"], seed) if next_is_free_hit else ""
        parts.append(_pick(t["noball"], seed).format(extra=extra, run_word=run_word(extra), free_hit=fh, **ctx))
        if is_boundary and runs_bat in (4, 6):
            parts.append(_pick(t["four" if runs_bat == 4 else "six"], seed).format(**ctx))
    elif byes:
        parts.append(_pick(t["bye"], seed).format(runs=byes, bye_word=t["bye"] if byes == 1 else t["byes"], **ctx))
    elif legbyes:
        parts.append(_pick(t["legbye"], seed).format(runs=legbyes, bye_word=t["bye"] if legbyes == 1 else t["byes"], **ctx))
    elif is_boundary and runs_bat == 4:
        parts.append(_pick(t["four"], seed).format(**ctx))
    elif is_boundary and runs_bat == 6:
        parts.append(_pick(t["six"], seed).format(**ctx))
    elif runs_bat == 0:
        if not wicket_kind:
            parts.append(_pick(t["dot"], seed).format(**ctx))
    else:
        parts.append(_pick(t["runs"], seed).format(runs=runs_bat, run_word=run_word(runs_bat), **ctx))
    if penalty_runs and not is_penalty_only:
        parts.append(_pick(t["penalty"], seed).format(runs=penalty_runs))
    if wicket_kind:
        if wicket_kind == "run_out":
            fby = t["fielder_by"].format(fielder=fielder) if fielder else ""
            parts.append(_pick(t["wicket_runout"], seed).format(player_out=player_out, fielder_by=fby))
        else:
            how = DISMISSALS[lang][wicket_kind].format(fielder=fielder or "")
            parts.append(_pick(t["wicket"], seed).format(player_out=player_out, how=how, bowler=bowler))
    return " ".join(p for p in parts if p).strip()


def retirement_commentary(lang, kind, player):
    lang = lang if lang in T else "en"
    return f"{player} — {DISMISSALS[lang][kind]}."


def over_end_commentary(lang, over_number, runs, score):
    lang = lang if lang in T else "en"
    t = T[lang]
    return t["over_end"].format(over=over_number, runs=runs, run_word=t["run"] if runs == 1 else t["runs_word"], score=score)
