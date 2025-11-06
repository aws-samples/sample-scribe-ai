/**
 * AppSync Events does not guarantee that subscribed events are the same order of published events.
 * This class try to process audio input/output events in the correct order using sequence number.
 */
export class AudioEventSequencer {
  private lastProcessedSequence = -1;
  private inputQueue: { [key: number]: string[] } = {};

  /**
   * @param processor the handler function to process a audio blobs (chunks).
   */
  public constructor(private processor: (chunks: string[]) => void) {}

  public next(chunks: string[], sequence: number) {
    let seq = sequence;
    if (seq <= this.lastProcessedSequence) {
      console.log(`skip sequence #${seq}`);
      return;
    }
    this.inputQueue[seq] = chunks;

    // we just enqueue the output without playback when a sequence is out of order.
    let processNow = false;
    if (seq == this.lastProcessedSequence + 1) {
      processNow = true;
    } else if (seq - this.lastProcessedSequence > 2) {
      // if a sequence is missing for more than 3 events, we ignore it and process the current sequence
      processNow = true;
    }

    if (processNow) {
      while (seq in this.inputQueue) {
        this.processor(this.inputQueue[seq]);
        delete this.inputQueue[seq];
        this.lastProcessedSequence = seq;
        seq++;
      }
    }
  }
}
