DROP TABLE IF EXISTS fact_claim CASCADE;
DROP TABLE IF EXISTS fact_member_month CASCADE;
DROP TABLE IF EXISTS dim_member CASCADE;
DROP TABLE IF EXISTS dim_provider CASCADE;

CREATE TABLE dim_provider (
    provider_id VARCHAR(32) PRIMARY KEY,
    provider_name VARCHAR(255) NOT NULL,
    provider_group VARCHAR(255) NOT NULL
);

CREATE TABLE dim_member (
    member_id VARCHAR(32) PRIMARY KEY,
    county VARCHAR(64) NOT NULL,
    age_group VARCHAR(32) NOT NULL,
    lob VARCHAR(32) NOT NULL
);

CREATE TABLE fact_member_month (
    member_id VARCHAR(32) NOT NULL REFERENCES dim_member(member_id),
    month_key VARCHAR(7) NOT NULL,
    member_months NUMERIC(10, 4) NOT NULL DEFAULT 1,
    PRIMARY KEY (member_id, month_key)
);

CREATE TABLE fact_claim (
    claim_id VARCHAR(32) PRIMARY KEY,
    member_id VARCHAR(32) NOT NULL REFERENCES dim_member(member_id),
    provider_id VARCHAR(32) NOT NULL REFERENCES dim_provider(provider_id),
    service_date DATE NOT NULL,
    paid_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    allowed_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    outstanding_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    claim_status VARCHAR(32) NOT NULL
);

CREATE INDEX idx_fact_claim_member ON fact_claim(member_id);
CREATE INDEX idx_fact_claim_provider ON fact_claim(provider_id);
CREATE INDEX idx_fact_claim_status ON fact_claim(claim_status);
CREATE INDEX idx_dim_member_county ON dim_member(county);
