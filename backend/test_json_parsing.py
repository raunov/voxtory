import json
import re
import sys
import os

# Add parent directory to sys.path to import from gemini_client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.gemini_client import GeminiClient

# Create a mock client instance for testing the JSON parsing functionality
client = GeminiClient()

# Test cases

# Test Case 1: Simple valid JSON
simple_json = '''{
  "transcript": [
    {"speaker": "Speaker Name", "timestamp": "00:00:00", "text": "Hello world"}
  ],
  "topics": ["Topic 1", "Topic 2"],
  "summary": "This is a test summary",
  "language": "English",
  "speakers": [
    {
      "name": "Speaker Name",
      "roles_affiliations": [
        {"role": "Current role", "affiliation": "Current affiliation"}
      ],
      "facts": ["Fact 1 about the speaker"],
      "views_beliefs": ["View 1"]
    }
  ]
}'''

# Test Case 2: JSON within markdown code blocks
markdown_json = '''
Here's the analysis result:

```json
{
  "transcript": [
    {"speaker": "Speaker 1", "timestamp": "00:00:00", "text": "Hello"}
  ],
  "topics": ["Topic A", "Topic B"],
  "summary": "Summary text here",
  "language": "English",
  "speakers": [{"name": "Speaker 1", "facts": ["Fact 1"]}]
}
```

I hope this helps!
'''

# Test Case 3: The complex real-world example from the user
complex_example = '''```json
{
  "transcript": [
    {
      "speaker": "Speaker 1",
      "timestamp": "00:00:00",
      "text": "teams which are technology and data, ICT skills, ICT money coming um with and services with legal knowledge. But here today I was asked to speak a bit about AI Act which is hopefully not new topic for you as you are just but with a bit of maybe twist what you needs what is useful to know from maybe startup perspective."
    },
    {
      "speaker": "Audience Member 2",
      "timestamp": "01:57:34",
      "text": "Okay, thank you, Stina."
    },
    {
      "speaker": "Host",
      "timestamp": "01:57:35",
      "text": "So next we have uh"
    }
  ],
  "topics": [
    "AI Act",
    "riskipõhine lähenemine",
    "keelatud AI praktikad",
    "kõrge riskiga AI süsteemid",
    "piiratud riskiga AI süsteemid",
    "minimaalne risk",
    "regulatiivne liivakast (regulatory sandbox)",
    "Euroopa Liidu investeeringud AI infrastruktuuri",
    "AI definitsioon",
    "juhised ja mallid"
  ],
  "summary": "Esineja räägib Euroopa Liidu AI Aktist, mis on riskipõhine lähenemine AI süsteemide reguleerimisele. Akt jagab AI süsteemid nelja riskikategooriasse: keelatud, kõrge riskiga, piiratud riskiga ja minimaalne risk. Kõrge riskiga süsteemidele kehtivad lisaregulatsioonid, samas kui minimaalse riskiga süsteeme ei reguleerita. Akti eesmärk on tasakaalustada innovatsiooni ja põhiõiguste kaitset. Ettevõtetele pakutakse regulatiivset liivakasti testimiseks ja juhiseid reeglite mõistmiseks. Euroopa Liit investeerib suuri summasid AI infrastruktuuri. Akti rakendamine toimub neljas etapis, enamik jõustub 2026. aastaks. Arutelu käigus küsitakse ühtse tõlgendamise ja Eesti konkurentsivõime kohta AI arenduses.",
  "language": "et",
  "speakers": [
    {
      "name": "Andrew (Speaker 1)",
      "roles_affiliations": [
        {
          "role": "esineja",
          "affiliation": "Ministeerium"
        }
      ],
      "facts": [
        "Esineb AI Akti teemal.",
        "Eesti AI regulatiivne liivakast on Justiits- ja digitaalvaldkonna ministeeriumi tasemel.",
        "Euroopa Liit investeerib 200 miljardit eurot AI infrastruktuuri.",
        "AI Akti jõustumine toimub neljas etapis, enamik 2026. aastaks."
      ],
      "views_beliefs": [
        "Praktikas võib AI Akti tõlgendamine liikmesriikides erineda sarnaselt GDPR-iga.",
        "Suuniste ja arutelude abil püütakse tagada AI definitsiooni ühtne mõistmine.",
        "Regulatiivsed liivakastid aitavad kaasa reeglite paremale mõistmisele ja ühtsele tõlgendamisele liikmesriikides."
      ]
    },
    {
      "name": "Audience Member 1",
      "roles_affiliations": [],
      "facts": [],
      "views_beliefs": [
        "GDPR-i puhul on probleemiks erinev tõlgendamine liikmesriikide andmekaitse järelevalveasutuste poolt.",
        "Küsimus, kas AI Aktiga suudetakse tagada ühtsem rakendamine kui GDPR-iga?",
        "Küsimus, mida Eesti teeb, et olla parem koht AI arendamiseks kui Soome või Saksamaa?"
      ]
    },
    {
      "name": "Audience Member 2",
      "roles_affiliations": [],
      "facts": [],
      "views_beliefs": [
        "Küsimus, kas EL ettevõte, mis arendab AI teenuseid EL-is, aga pakub neid väljaspool EL-i, peab AI Akti järgima?"
      ]
    },
    {
      "name": "Host",
      "roles_affiliations": [],
      "facts": [],
      "views_beliefs": []
    }
  ]
}
```'''

def test_parsing_strategy(test_case_name, text):
    print(f"\n=== Testing: {test_case_name} ===\n")
    
    result = client._extract_and_parse_json(text)
    
    if isinstance(result["result"], dict):
        print(f"✅ SUCCESS: Parsed {test_case_name} successfully")
        
        # Verify expected structure
        parsed_json = result["result"]
        if "transcript" in parsed_json and "speakers" in parsed_json:
            print("✅ JSON has expected structure with transcript and speakers")
        else:
            print("❌ WARNING: JSON missing expected keys")
            
        # Print first few keys to verify content
        print(f"Keys found: {list(parsed_json.keys())}")
        print(f"Number of transcript entries: {len(parsed_json.get('transcript', []))}")
        print(f"Number of speakers: {len(parsed_json.get('speakers', []))}")
    else:
        print(f"❌ FAILED: Could not parse {test_case_name} as JSON")
        print(f"Result type: {type(result['result'])}")

# Run tests
print("Testing JSON parsing strategies")
print("==============================\n")

test_parsing_strategy("Simple valid JSON", simple_json)
test_parsing_strategy("JSON within markdown code blocks", markdown_json)
test_parsing_strategy("Complex real-world example", complex_example)

print("\n\nAll tests completed.")
