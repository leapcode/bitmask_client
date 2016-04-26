.PHONY: all pkg installer openvpn pyinstaller
all:
	docker-compose build
	$(MAKE) pkg

pkg:
	$(MAKE) openvpn
	$(MAKE) pyinstaller
	$(MAKE) installer

pyinstaller:
	docker-compose run --rm pyinstaller

openvpn:
	docker-compose run --rm openvpn

installer:
	docker-compose run --rm installer

clean:
	docker rmi windows_pyinstaller
	docker rmi windows_openvpn
	docker rmi windows_installer
	rm -rf ../../dist/*.exe
	rm -rf ../../build/*