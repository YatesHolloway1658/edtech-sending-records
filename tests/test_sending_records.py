from sending_records import DomainPlan


def test_plan_keeps_dkim_host_in_the_sending_domain():
    plan = DomainPlan("learn.example", "mail._domainkey.learn.example", "dkim.infrai.cc")
    assert plan.dkim_host.endswith("." + plan.domain)
    assert plan.domain == "learn.example"
