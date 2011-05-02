all: deps test

deps:

specloud:
	@python -c 'import specloud' 2>/dev/null || pip install --no-deps specloud -r http://github.com/hugobr/specloud/raw/master/requirements.txt

should-dsl:
	@python -c 'import should_dsl' 2>/dev/null || pip install http://github.com/hugobr/should-dsl/tarball/master

test: unit

unit: specloud should-dsl
	@echo =======================================
	@echo ========= Running unit specs ==========
	@specloud spec
	@echo

