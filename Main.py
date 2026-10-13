import newsongs
import playback
import time

def main():
    while True:
        try:

            choose = int(input("1 For Add new song \n2 To play the Playlist: "))
            if choose == 1:
                time.sleep(0.2)
                newsongs.new()
            elif choose == 2 :
                time.sleep(0.2)
                playback.new()
                continue
            elif choose == 0:
                print("Bye")
                break
            else:
                print("Not a choice !")
        except ValueError :
            print("Not a choice !")
            continue 
    

main()        