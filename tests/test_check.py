"""decide() of check_and_retrain.py: one test per possible answer (task 5.2)."""
import yaml

from check_and_retrain import decide

POLICY = yaml.safe_load(open("policy.yaml"))  # min_new_days 3, psi_act 0.25, cooldown_days 7


def test_wait_when_too_few_new_days():
    assert decide(psi_max=1.0, days=2, days_since_retrain=None, policy=POLICY) == "wait"


def test_watch_when_inputs_did_not_move():
    assert decide(psi_max=0.12, days=7, days_since_retrain=None, policy=POLICY) == "watch"


def test_cooldown_after_a_recent_retrain():
    assert decide(psi_max=1.0, days=7, days_since_retrain=0.0, policy=POLICY) == "cooldown"


def test_retrain_when_drift_and_never_retrained():
    assert decide(psi_max=1.0, days=7, days_since_retrain=None, policy=POLICY) == "retrain"


def test_retrain_again_once_the_cooldown_is_over():
    assert decide(psi_max=1.0, days=7, days_since_retrain=8.0, policy=POLICY) == "retrain"
