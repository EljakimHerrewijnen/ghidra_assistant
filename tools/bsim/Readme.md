# BSIM helpers

Code from [this repository](https://github.com/ckane/ghidra-bsim-elastic) used.

## Steps
Run ``sudo setup.sh``, which should *mostly* work. If you want an updated version, edit the Dockerfile in ``elastic-bsim`` with a newer ghidra version.
```bash
$ sudo setup.sh
```

### Nginx
I added a nginx entry to be able to connect to bsim.herreweb.nl from a remote location. This also solves SSL errors.
bsim.herreweb.nl -> 192.168.0.160:9200

### Environment
Setup the .env properly:
```
GHIDRA_ROOT="$(pwd)/ghidra"
ELASTIC_URL="https://bsim.herreweb.nl"

# Will be auto-populated, so leave empty at first
ELASTIC_PASSWORD=
```

```bash
$ ./add_user.sh eljakim somepassword
$ $REVERSEENVGHIDRADIR/support/bsim createdatabase elastic://bsim.herreweb.nl:443/bsim medium_nosize --name Herreweb
```
You will be asked for a password, provide teh previously inserted password.


## Other tools
see $REVERSEENVGHIDRADIR/support/bsim for more commands


```
$REVERSEENVGHIDRADIR/support/bsim generatesigs ghidra://192.168.0.160/Pixel/synacktiv/evt.ec.bin --bsim elastic://bsim.herreweb.nl:443/bsim --commit
$REVERSEENVGHIDRADIR/support/bsim listexes elastic://bsim.herreweb.nl:443/bsim
```