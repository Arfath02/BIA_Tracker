-- Preserving v9 -> v10 upgrade. BACK UP and STOP the API first.
-- Run as DBA in the dedicated BIA database. No business rows are deleted.
-- After success reapply 02_runtime_permissions.sql, then start the new API.
SET XACT_ABORT ON;
BEGIN TRY
BEGIN TRANSACTION;
IF EXISTS (SELECT 1 FROM bia.schema_migrations WHERE version=10)
BEGIN
    COMMIT TRANSACTION;
    PRINT 'Schema v10 already installed.';
    RETURN;
END;
IF NOT EXISTS (SELECT 1 FROM bia.schema_migrations WHERE version=9)
    THROW 51000, 'This script requires schema v9. For earlier versions use deploy/migrate.py.', 1;



CREATE TABLE bia.currency_codes (
	code VARCHAR(3) NOT NULL, 
	name NVARCHAR(100) NOT NULL, 
	digits INTEGER NOT NULL, 
	CONSTRAINT pk_currency_codes PRIMARY KEY (code), 
	CONSTRAINT ck_currency_codes_digits_range CHECK (digits>=0 AND digits<=4)
)

;


CREATE TABLE bia.project_finance (
	[projectId] VARCHAR(36) NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	[usdRate] NUMERIC(18, 8) NOT NULL, 
	[rateDate] DATE NULL, 
	[vendorId] VARCHAR(36) NULL, 
	CONSTRAINT pk_project_finance PRIMARY KEY ([projectId]), 
	CONSTRAINT ck_project_finance_rate_positive CHECK (usdRate>0), 
	CONSTRAINT ck_project_finance_usd_rate_one CHECK (currency<>'USD' OR usdRate=1), 
	CONSTRAINT [fk_project_finance_projectId_projects] FOREIGN KEY([projectId]) REFERENCES bia.projects (id), 
	CONSTRAINT fk_project_finance_currency_currency_codes FOREIGN KEY(currency) REFERENCES bia.currency_codes (code), 
	CONSTRAINT [fk_project_finance_vendorId_vendors] FOREIGN KEY([vendorId]) REFERENCES bia.vendors (id)
)

;

CREATE INDEX [ix_project_finance_vendorId] ON bia.project_finance ([vendorId]);


CREATE TABLE bia.vendor_consultants (
	id VARCHAR(36) NOT NULL, 
	[vendorId] VARCHAR(36) NOT NULL, 
	[ownerProjectId] VARCHAR(36) NULL, 
	name NVARCHAR(100) COLLATE Latin1_General_100_CI_AS_SC NOT NULL, 
	active BIT NOT NULL, 
	CONSTRAINT pk_vendor_consultants PRIMARY KEY (id), 
	CONSTRAINT [uq_vendor_consultants_vendorId] UNIQUE ([vendorId], name), 
	CONSTRAINT [fk_vendor_consultants_vendorId_vendors] FOREIGN KEY([vendorId]) REFERENCES bia.vendors (id), 
	CONSTRAINT [fk_vendor_consultants_ownerProjectId_projects] FOREIGN KEY([ownerProjectId]) REFERENCES bia.projects (id)
)

;

CREATE INDEX [ix_vendor_consultants_vendorId] ON bia.vendor_consultants ([vendorId]);

CREATE INDEX [ix_vendor_consultants_ownerProjectId] ON bia.vendor_consultants ([ownerProjectId]);


CREATE TABLE bia.consultant_trips (
	id VARCHAR(36) NOT NULL, 
	[projectId] VARCHAR(36) NOT NULL, 
	[consultantId] VARCHAR(36) NOT NULL, 
	start DATE NOT NULL, 
	[end] DATE NOT NULL, 
	[biaFlight] BIT NOT NULL, 
	[biaAccommodation] BIT NOT NULL, 
	[biaFood] BIT NOT NULL, 
	[stayType] VARCHAR(20) NULL, 
	[flightBooked] BIT NOT NULL, 
	[flightCost] NUMERIC(19, 4) NULL, 
	[bookedDate] DATE NULL, 
	notes NVARCHAR(1000) NOT NULL, 
	CONSTRAINT pk_consultant_trips PRIMARY KEY (id), 
	CONSTRAINT ck_consultant_trips_dates_ordered CHECK ([end]>=start), 
	CONSTRAINT ck_consultant_trips_stay_valid CHECK ((biaAccommodation=0 AND stayType IS NULL) OR (biaAccommodation=1 AND stayType IN ('campus','external'))), 
	CONSTRAINT ck_consultant_trips_flight_valid CHECK ((flightBooked=0 AND flightCost IS NULL AND bookedDate IS NULL) OR (flightBooked=1 AND biaFlight=1 AND flightCost>0 AND bookedDate IS NOT NULL AND bookedDate<=start)), 
	CONSTRAINT [fk_consultant_trips_projectId_projects] FOREIGN KEY([projectId]) REFERENCES bia.projects (id), 
	CONSTRAINT [fk_consultant_trips_consultantId_vendor_consultants] FOREIGN KEY([consultantId]) REFERENCES bia.vendor_consultants (id)
)

;

CREATE INDEX [ix_consultant_trips_projectId] ON bia.consultant_trips ([projectId]);

CREATE INDEX [ix_consultant_trips_consultantId] ON bia.consultant_trips ([consultantId]);


CREATE TABLE bia.payment_terms (
	id VARCHAR(36) NOT NULL, 
	[projectId] VARCHAR(36) NOT NULL, 
	title NVARCHAR(100) NOT NULL, 
	amount NUMERIC(19, 4) NOT NULL, 
	[trigger] VARCHAR(20) NOT NULL, 
	[dueDate] DATE NULL, 
	[milestoneId] VARCHAR(36) NULL, 
	cancelled BIT NOT NULL, 
	CONSTRAINT pk_payment_terms PRIMARY KEY (id), 
	CONSTRAINT fk_terms_milestone_project FOREIGN KEY([milestoneId], [projectId]) REFERENCES bia.tasks (id, [projectId]), 
	CONSTRAINT ck_payment_terms_amount_positive CHECK (amount>0), 
	CONSTRAINT ck_payment_terms_valid_trigger CHECK (([trigger]='date' AND dueDate IS NOT NULL AND milestoneId IS NULL) OR ([trigger]='milestone' AND dueDate IS NULL AND milestoneId IS NOT NULL)), 
	CONSTRAINT [fk_payment_terms_projectId_projects] FOREIGN KEY([projectId]) REFERENCES bia.projects (id)
)

;

CREATE INDEX [ix_payment_terms_projectId] ON bia.payment_terms ([projectId]);


CREATE TABLE bia.invoice_terms (
	[invoiceId] VARCHAR(36) NOT NULL, 
	[termId] VARCHAR(36) NOT NULL, 
	CONSTRAINT pk_invoice_terms PRIMARY KEY ([invoiceId]), 
	CONSTRAINT [fk_invoice_terms_invoiceId_invoices] FOREIGN KEY([invoiceId]) REFERENCES bia.invoices (id), 
	CONSTRAINT [uq_invoice_terms_termId] UNIQUE ([termId]), 
	CONSTRAINT [fk_invoice_terms_termId_payment_terms] FOREIGN KEY([termId]) REFERENCES bia.payment_terms (id)
)

;

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('AED', N'UAE Dirham', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('AFN', N'Afghani', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ALL', N'Lek', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('AMD', N'Armenian Dram', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('AOA', N'Kwanza', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ARS', N'Argentine Peso', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('AUD', N'Australian Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('AWG', N'Aruban Florin', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('AZN', N'Azerbaijan Manat', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BAM', N'Convertible Mark', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BBD', N'Barbados Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BDT', N'Taka', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BHD', N'Bahraini Dinar', 3);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BIF', N'Burundi Franc', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BMD', N'Bermudian Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BND', N'Brunei Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BOB', N'Boliviano', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BOV', N'Mvdol', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BRL', N'Brazilian Real', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BSD', N'Bahamian Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BTN', N'Ngultrum', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BWP', N'Pula', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BYN', N'Belarusian Ruble', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('BZD', N'Belize Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CAD', N'Canadian Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CDF', N'Congolese Franc', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CHE', N'WIR Euro', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CHF', N'Swiss Franc', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CHW', N'WIR Franc', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CLF', N'Unidad de Fomento', 4);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CLP', N'Chilean Peso', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CNY', N'Yuan Renminbi', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('COP', N'Colombian Peso', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('COU', N'Unidad de Valor Real', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CRC', N'Costa Rican Colon', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CUP', N'Cuban Peso', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CVE', N'Cabo Verde Escudo', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('CZK', N'Czech Koruna', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('DJF', N'Djibouti Franc', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('DKK', N'Danish Krone', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('DOP', N'Dominican Peso', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('DZD', N'Algerian Dinar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('EGP', N'Egyptian Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ERN', N'Nakfa', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ETB', N'Ethiopian Birr', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('EUR', N'Euro', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('FJD', N'Fiji Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('FKP', N'Falkland Islands Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GBP', N'Pound Sterling', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GEL', N'Lari', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GHS', N'Ghana Cedi', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GIP', N'Gibraltar Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GMD', N'Dalasi', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GNF', N'Guinean Franc', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GTQ', N'Quetzal', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('GYD', N'Guyana Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('HKD', N'Hong Kong Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('HNL', N'Lempira', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('HTG', N'Gourde', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('HUF', N'Forint', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('IDR', N'Rupiah', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ILS', N'New Israeli Sheqel', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('INR', N'Indian Rupee', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('IQD', N'Iraqi Dinar', 3);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('IRR', N'Iranian Rial', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ISK', N'Iceland Krona', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('JMD', N'Jamaican Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('JOD', N'Jordanian Dinar', 3);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('JPY', N'Yen', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KES', N'Kenyan Shilling', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KGS', N'Som', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KHR', N'Riel', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KMF', N'Comorian Franc ', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KPW', N'North Korean Won', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KRW', N'Won', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KWD', N'Kuwaiti Dinar', 3);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KYD', N'Cayman Islands Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('KZT', N'Tenge', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('LAK', N'Lao Kip', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('LBP', N'Lebanese Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('LKR', N'Sri Lanka Rupee', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('LRD', N'Liberian Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('LSL', N'Loti', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('LYD', N'Libyan Dinar', 3);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MAD', N'Moroccan Dirham', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MDL', N'Moldovan Leu', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MGA', N'Malagasy Ariary', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MKD', N'Denar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MMK', N'Kyat', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MNT', N'Tugrik', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MOP', N'Pataca', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MRU', N'Ouguiya', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MUR', N'Mauritius Rupee', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MVR', N'Rufiyaa', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MWK', N'Malawi Kwacha', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MXN', N'Mexican Peso', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MXV', N'Mexican Unidad de Inversion (UDI)', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MYR', N'Malaysian Ringgit', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('MZN', N'Mozambique Metical', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('NAD', N'Namibia Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('NGN', N'Naira', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('NIO', N'Cordoba Oro', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('NOK', N'Norwegian Krone', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('NPR', N'Nepalese Rupee', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('NZD', N'New Zealand Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('OMR', N'Rial Omani', 3);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('PAB', N'Balboa', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('PEN', N'Sol', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('PGK', N'Kina', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('PHP', N'Philippine Peso', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('PKR', N'Pakistan Rupee', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('PLN', N'Zloty', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('PYG', N'Guarani', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('QAR', N'Qatari Rial', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('RON', N'Romanian Leu', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('RSD', N'Serbian Dinar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('RUB', N'Russian Ruble', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('RWF', N'Rwanda Franc', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SAR', N'Saudi Riyal', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SBD', N'Solomon Islands Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SCR', N'Seychelles Rupee', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SDG', N'Sudanese Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SEK', N'Swedish Krona', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SGD', N'Singapore Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SHP', N'Saint Helena Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SLE', N'Leone', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SOS', N'Somali Shilling', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SRD', N'Surinam Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SSP', N'South Sudanese Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('STN', N'Dobra', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SVC', N'El Salvador Colon', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SYP', N'Syrian Pound', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('SZL', N'Lilangeni', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('THB', N'Baht', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TJS', N'Somoni', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TMT', N'Turkmenistan New Manat', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TND', N'Tunisian Dinar', 3);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TOP', N'Pa’anga', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TRY', N'Turkish Lira', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TTD', N'Trinidad and Tobago Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TWD', N'New Taiwan Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('TZS', N'Tanzanian Shilling', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('UAH', N'Hryvnia', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('UGX', N'Uganda Shilling', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('USD', N'US Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('USN', N'US Dollar (Next day)', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('UYI', N'Uruguay Peso en Unidades Indexadas (UI)', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('UYU', N'Peso Uruguayo', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('UYW', N'Unidad Previsional', 4);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('UZS', N'Uzbekistan Sum', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('VED', N'Bolívar Soberano', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('VES', N'Bolívar Soberano', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('VND', N'Dong', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('VUV', N'Vatu', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('WST', N'Tala', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('XAD', N'Arab Accounting Dinar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('XAF', N'CFA Franc BEAC', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('XCD', N'East Caribbean Dollar', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('XCG', N'Caribbean Guilder', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('XOF', N'CFA Franc BCEAO', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('XPF', N'CFP Franc', 0);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('YER', N'Yemeni Rial', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ZAR', N'Rand', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ZMW', N'Zambian Kwacha', 2);

INSERT INTO bia.currency_codes (code, name, digits) VALUES ('ZWG', N'Zimbabwe Gold', 2);

ALTER TABLE bia.projects DROP CONSTRAINT ck_projects_budget_nonnegative;
ALTER TABLE bia.projects ALTER COLUMN budget DECIMAL(19,4) NOT NULL;
ALTER TABLE bia.projects WITH CHECK ADD CONSTRAINT ck_projects_budget_nonnegative CHECK (budget>=0);

ALTER TABLE bia.purchase_orders DROP CONSTRAINT ck_purchase_orders_amount_positive;
ALTER TABLE bia.purchase_orders ALTER COLUMN amount DECIMAL(19,4) NOT NULL;
ALTER TABLE bia.purchase_orders WITH CHECK ADD CONSTRAINT ck_purchase_orders_amount_positive CHECK (amount>0);

ALTER TABLE bia.invoices DROP CONSTRAINT ck_invoices_amount_positive;
ALTER TABLE bia.invoices ALTER COLUMN amount DECIMAL(19,4) NOT NULL;
ALTER TABLE bia.invoices WITH CHECK ADD CONSTRAINT ck_invoices_amount_positive CHECK (amount>0);

INSERT INTO bia.project_finance(projectId,currency,usdRate,rateDate,vendorId)
SELECT id,'USD',1,NULL,NULL FROM bia.projects;
INSERT INTO bia.schema_migrations(version,appliedAt) VALUES(10,SYSUTCDATETIME());
COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
