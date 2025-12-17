import pytest
from senytl import behavior

class MockResponse:
    def __init__(self, text):
        self.text = text

def test_behavior_assertions():
    r_empathetic = MockResponse("I am sorry to hear that you are having trouble.")
    behavior.assert_empathetic(r_empathetic)
    
    r_rude = MockResponse("That's too bad.")
    with pytest.raises(behavior.BehaviorError):
        behavior.assert_empathetic(r_rude)
        
    r_prof = MockResponse("We will examine the issue.")
    behavior.assert_professional(r_prof)
    
    r_slang = MockResponse("lol that sucks.")
    with pytest.raises(behavior.BehaviorError):
        behavior.assert_professional(r_slang)
        
    r_def = MockResponse("It's not our fault you broke it.")
    with pytest.raises(behavior.BehaviorError):
        behavior.assert_no_defensiveness(r_def)
        
    r_sol = MockResponse("We can refund your purchase.")
    behavior.assert_offers_solution(r_sol)
    
    r_harm = MockResponse("You should kill the process.") 
    with pytest.raises(behavior.BehaviorError):
        behavior.assert_no_harmful_content(r_harm)

def test_custom_rule():
    @behavior.define("must_say_please")
    def check_please(response):
        return "please" in response.text.lower()
        
    r_polite = MockResponse("Please wait.")
    behavior.assert_follows("must_say_please", r_polite)
    
    r_rude = MockResponse("Wait.")
    with pytest.raises(behavior.BehaviorError):
        behavior.assert_follows("must_say_please", r_rude)
        
    with pytest.raises(ValueError):
        behavior.assert_follows("unknown_rule", r_polite)
