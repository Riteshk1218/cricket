import 'package:flutter/widgets.dart';
import 'package:provider/provider.dart';

import 'app_state.dart';

/// UI strings in English, Marathi and Hindi. Commentary text comes from the
/// server in all three languages, so only interface labels live here.
const Map<String, Map<String, String>> _strings = {
  'en': {
    'app': 'CricLive', 'home': 'Home', 'live': 'Live', 'matches': 'Matches', 'tournaments': 'Tournaments',
    'teams': 'Teams', 'players': 'Players', 'more': 'More', 'live_now': 'Live now', 'upcoming': 'Upcoming',
    'results': 'Results', 'fixtures': 'Fixtures', 'points': 'Points table', 'leaders': 'Leaders',
    'scorecard': 'Scorecard', 'commentary': 'Commentary', 'overs': 'Overs', 'info': 'Info',
    'login': 'Log in', 'logout': 'Log out', 'register': 'Create account', 'username': 'Username',
    'password': 'Password', 'email': 'Email', 'name': 'Display name', 'settings': 'Settings',
    'profile': 'Profile', 'server': 'Server address', 'language': 'Language', 'theme': 'Theme',
    'sound': 'Sound effects', 'volume': 'Volume', 'animations': 'Animations', 'scorer': 'Scorer',
    'my_matches': 'My scoring matches', 'no_live': 'No live matches right now.', 'retry': 'Retry',
    'nothing': 'Nothing here yet.', 'target': 'Target', 'crr': 'CRR', 'rrr': 'RRR', 'free_hit': 'FREE HIT',
    'batting': 'Batting', 'bowling': 'Bowling', 'extras': 'Extras', 'total': 'Total', 'fow': 'Fall of wickets',
    'yet_to_bat': 'Yet to bat', 'viewers': 'watching', 'reconnecting': 'Reconnecting…', 'connected': 'Live',
    'toss': 'Toss', 'venue': 'Venue', 'search': 'Search', 'save': 'Save', 'test_connection': 'Test connection',
    'guest': 'Browsing as guest', 'stats': 'Stats', 'four': 'FOUR!', 'six': 'SIX!', 'wicket': 'WICKET!',
    'paused': 'Paused', 'system': 'System', 'light': 'Light', 'dark': 'Dark',
  },
  'mr': {
    'app': 'क्रिकलाइव्ह', 'home': 'मुख्यपृष्ठ', 'live': 'थेट', 'matches': 'सामने', 'tournaments': 'स्पर्धा',
    'teams': 'संघ', 'players': 'खेळाडू', 'more': 'अधिक', 'live_now': 'आता थेट', 'upcoming': 'आगामी',
    'results': 'निकाल', 'fixtures': 'वेळापत्रक', 'points': 'गुणतालिका', 'leaders': 'आघाडीचे खेळाडू',
    'scorecard': 'धावफलक', 'commentary': 'समालोचन', 'overs': 'षटके', 'info': 'माहिती',
    'login': 'लॉग इन', 'logout': 'लॉग आउट', 'register': 'खाते तयार करा', 'username': 'वापरकर्ता नाव',
    'password': 'पासवर्ड', 'email': 'ईमेल', 'name': 'नाव', 'settings': 'सेटिंग्ज',
    'profile': 'प्रोफाइल', 'server': 'सर्व्हर पत्ता', 'language': 'भाषा', 'theme': 'थीम',
    'sound': 'आवाज', 'volume': 'आवाजाची पातळी', 'animations': 'ॲनिमेशन', 'scorer': 'स्कोअरर',
    'my_matches': 'माझे स्कोअरिंग सामने', 'no_live': 'सध्या कोणताही थेट सामना नाही.', 'retry': 'पुन्हा प्रयत्न करा',
    'nothing': 'अजून काही नाही.', 'target': 'लक्ष्य', 'crr': 'सध्याचा रनरेट', 'rrr': 'आवश्यक रनरेट', 'free_hit': 'फ्री हिट',
    'batting': 'फलंदाजी', 'bowling': 'गोलंदाजी', 'extras': 'अवांतर', 'total': 'एकूण', 'fow': 'विकेट पडण्याचा क्रम',
    'yet_to_bat': 'फलंदाजी बाकी', 'viewers': 'पाहत आहेत', 'reconnecting': 'पुन्हा जोडत आहे…', 'connected': 'थेट',
    'toss': 'नाणेफेक', 'venue': 'मैदान', 'search': 'शोधा', 'save': 'जतन करा', 'test_connection': 'कनेक्शन तपासा',
    'guest': 'पाहुणे म्हणून पाहत आहात', 'stats': 'आकडेवारी', 'four': 'चौकार!', 'six': 'षटकार!', 'wicket': 'विकेट!',
    'paused': 'थांबवले', 'system': 'सिस्टम', 'light': 'लाइट', 'dark': 'डार्क',
  },
  'hi': {
    'app': 'क्रिकलाइव', 'home': 'होम', 'live': 'लाइव', 'matches': 'मैच', 'tournaments': 'टूर्नामेंट',
    'teams': 'टीमें', 'players': 'खिलाड़ी', 'more': 'और', 'live_now': 'अभी लाइव', 'upcoming': 'आगामी',
    'results': 'परिणाम', 'fixtures': 'कार्यक्रम', 'points': 'अंक तालिका', 'leaders': 'शीर्ष खिलाड़ी',
    'scorecard': 'स्कोरकार्ड', 'commentary': 'कमेंट्री', 'overs': 'ओवर', 'info': 'जानकारी',
    'login': 'लॉग इन', 'logout': 'लॉग आउट', 'register': 'खाता बनाएं', 'username': 'यूज़रनेम',
    'password': 'पासवर्ड', 'email': 'ईमेल', 'name': 'नाम', 'settings': 'सेटिंग्स',
    'profile': 'प्रोफ़ाइल', 'server': 'सर्वर पता', 'language': 'भाषा', 'theme': 'थीम',
    'sound': 'ध्वनि', 'volume': 'वॉल्यूम', 'animations': 'एनिमेशन', 'scorer': 'स्कोरर',
    'my_matches': 'मेरे स्कोरिंग मैच', 'no_live': 'अभी कोई लाइव मैच नहीं है।', 'retry': 'फिर से कोशिश करें',
    'nothing': 'अभी कुछ नहीं है।', 'target': 'लक्ष्य', 'crr': 'मौजूदा रन रेट', 'rrr': 'आवश्यक रन रेट', 'free_hit': 'फ्री हिट',
    'batting': 'बल्लेबाज़ी', 'bowling': 'गेंदबाज़ी', 'extras': 'अतिरिक्त', 'total': 'कुल', 'fow': 'विकेट पतन',
    'yet_to_bat': 'बल्लेबाज़ी बाकी', 'viewers': 'देख रहे हैं', 'reconnecting': 'फिर से जुड़ रहा है…', 'connected': 'लाइव',
    'toss': 'टॉस', 'venue': 'मैदान', 'search': 'खोजें', 'save': 'सहेजें', 'test_connection': 'कनेक्शन जांचें',
    'guest': 'मेहमान के रूप में देख रहे हैं', 'stats': 'आंकड़े', 'four': 'चौका!', 'six': 'छक्का!', 'wicket': 'विकेट!',
    'paused': 'रुका हुआ', 'system': 'सिस्टम', 'light': 'लाइट', 'dark': 'डार्क',
  },
};

const languages = {'en': 'English', 'mr': 'मराठी', 'hi': 'हिंदी'};

String tr(String lang, String key) => _strings[lang]?[key] ?? _strings['en']![key] ?? key;

extension Tr on BuildContext {
  /// Translate a UI key using the current language (rebuilds when it changes).
  String t(String key) => tr(watch<AppState>().language, key);
}
