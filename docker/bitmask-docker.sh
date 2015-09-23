#!/bin/bash

run(){
    # NOTE: you may need this line if you get an error using ip6tables
    # (host needs ip6 kernel modules to use it in the container)
    # sudo modprobe ip6_tables

    # NOTE: to get X11 socket forwarding to work we need this
    xhost local:root

    CREDS_OPTS=''
    if [[ -n $BITMASK_CREDENTIALS ]]; then
        BITMASK_CREDENTIALS=`realpath $BITMASK_CREDENTIALS`
        CREDS_OPTS="-e BITMASK_CREDENTIALS=/data/credentials.ini -v $BITMASK_CREDENTIALS:/data/credentials.ini"
    fi

    docker run --rm -it \
        --net host \
        --privileged \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -e DISPLAY=unix$DISPLAY \
        $CREDS_OPTS \
        -v `pwd`/data/:/data/ -v `pwd`:/SHARED/ \
        -v `pwd`/data/config:/root/.config/leap \
        -p 1984:1984 -p 2013:2013 \
        --name bitmask \
        test/bitmask run $@

    # Services' related ports
    # eip: ["80", "53", "443", "1194"]
    # mail: ["1984", "2013"]

    # logs when no ip6_tables module is not loaded on host:
    # root@bitmask-container:/bitmask# sudo ip6tables --new-chain bitmask
    # modprobe: ERROR: ../libkmod/libkmod.c:556 kmod_search_moddep() could not open moddep file '/lib/modules/4.1.6-040106-generic/modules.dep.bin'
    # ip6tables v1.4.21: can't initialize ip6tables table `filter': Table does not exist (do you need to insmod?)
    # Perhaps ip6tables or your kernel needs to be upgraded.

    # logs when ip6_tables module is loaded on host:
    # root@bitmask-container:/bitmask# sudo ip6tables --new-chain bitmask
    # root@bitmask-container:/bitmask# # success!
}

shell(){
    xhost local:root

    docker run --rm -it \
        --net host \
        --privileged \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -e DISPLAY=unix$DISPLAY \
        -v `pwd`/data/:/data/ -v `pwd`:/SHARED/ \
        -v `pwd`/data/config:/root/.config/leap \
        -p 1984:1984 -p 2013:2013 \
        --name bitmask \
        --entrypoint=bash \
        test/bitmask
}

init(){
    JSON=`realpath $1`
    docker run --rm -it \
        -v `pwd`/data:/data \
        -v $JSON:/shared/bitmask.json \
        test/bitmask init ro /shared/bitmask.json
}

update(){
    JSON=`realpath $1`
    docker run --rm -it \
        -v `pwd`/data:/data \
        -v $JSON:/shared/bitmask.json \
        test/bitmask update /shared/bitmask.json
}

build(){
    docker build -t test/bitmask .
}

help() {
    echo ">> Bitmask on docker"
    echo "Run the bitmask app in a docker container."
    echo
    echo "Usage: $0 {init bitmask.json | update bitmask.json | build | shell | run | help}"
    echo        
    echo "  ?.json : The bitmask*.json file describes the version that will be used for each repo."
    echo
    echo "    init : Clone repositories, install dependencies, and get bitmask ready to be used."
    echo "  update : Update the repositories and install new deps (if needed)."
    echo "   build : Build the docker image for bitmask."
    echo "   shell : Run a shell inside a bitmask docker container (useful to debug)."
    echo "     run : Run the client (any extra parameters will be sent to the app)."
    echo "    help : Show this help"
    echo
}


case "$1" in
    run)
        run "$@"
        ;;
    init)
        init $2
        ;;
    update)
        update $2
        ;;
    build)
        build
        ;;
    shell)
        shell
        ;;
    *)
        help
        ;;
esac
