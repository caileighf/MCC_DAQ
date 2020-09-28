import time
import simpleaudio as sa
import argparse
from prompt_toolkit import prompt

def main(args):
    prompt('Hit enter when the test leads are connected to the payload box and the DAQs are running.')

    wave_obj = sa.WaveObject.from_wave_file(args.wav_file)
    play_obj = wave_obj.play()
    start_t = time.time()
    print('Tone started at {}'.format(start_t))

    while play_obj.is_playing():
        if args.playback_duration != None:
            if time.time() - start_t >= args.playback_duration:
                break
        if args.pulse:
            play_obj.stop()
            time.sleep(0.3)
            play_obj.play()

    play_obj.stop()
    print('Tone stopped at {}'.format(time.time()))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--wav-file', help='.wav files to play', default='singletone.wav', type=str)
    parser.add_argument('--pulse', help='Show debugging print messages', action='store_true')
    parser.add_argument('--playback-duration', 
                        help='max duration to play .wav file if None play entire file', 
                        default=None, type=int)
    args = parser.parse_args()

    try:
        main(args)
    except KeyboardInterrupt:
        pass
    finally:
        print('\n\tExiting...\n')


