package main

import (
	"log"
	"net/http"
)

func main() {
	store := NewStore(6)
	srv := NewServer(store)

	addr := ":8080"
	log.Printf("url shortener listening on %s", addr)
	if err := http.ListenAndServe(addr, srv.Handler()); err != nil {
		log.Fatal(err)
	}
}
