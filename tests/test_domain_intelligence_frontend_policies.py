from forge.domain_intelligence.frontend.policies import DomainIntelligencePolicy


def test_frontend_policy_is_read_only_by_default() -> None:
    policy = DomainIntelligencePolicy()

    assert not policy.allow_network
    assert not policy.allow_source_modification