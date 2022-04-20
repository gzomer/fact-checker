//
//  ViewController.swift
//  FactChecker
//
//  Created by Gustavo Zomer on 04/04/2022.
//  Copyright © 2022 Gustavo Zomer. All rights reserved.
//

import UIKit
import Speech

class ViewController: UIViewController, SFSpeechRecognizerDelegate {

    @IBOutlet weak var textView: UITextView!
    @IBOutlet weak var titleLabel: UILabel!
    @IBOutlet weak var descriptionLabel: UILabel!
    @IBOutlet weak var veracityLabel: UILabel!
    @IBOutlet weak var microphoneButton: UIButton!
    @IBOutlet weak var sourceButton: UIButton!

    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))!

    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?

    private var recognitionTask: SFSpeechRecognitionTask?

    private let audioEngine = AVAudioEngine()
    private var sourceURL: String!
    private var openedBySiri: Bool = false

    override func viewDidLoad() {
        super.viewDidLoad()
        hideResult()
        microphoneButton.isEnabled = false
        speechRecognizer.delegate = self

        SFSpeechRecognizer.requestAuthorization { authStatus in
            OperationQueue.main.addOperation {
                switch authStatus {
                case .authorized:
                    self.microphoneButton.isEnabled = true
                    self.microphoneTapped(self)
                case .denied:
                    self.microphoneButton.isEnabled = false
                    self.descriptionLabel.text = "User denied access to speech recognition"
                case .restricted:
                    self.microphoneButton.isEnabled = false
                    self.descriptionLabel.text = "Speech recognition restricted on this device"
                case .notDetermined:
                    self.microphoneButton.isEnabled = false
                    self.descriptionLabel.text = "Speech recognition not yet authorized"
                @unknown default:
                    self.microphoneButton.isEnabled = false
                    self.descriptionLabel.text = "Speech recognition not yet authorized"
                }
            }
        }
    }

    override var preferredStatusBarStyle: UIStatusBarStyle {
        return .lightContent
    }

    @IBAction func microphoneTapped(_ sender: AnyObject) {
        if audioEngine.isRunning {
            audioEngine.stop()
            recognitionRequest?.endAudio()
            microphoneButton.setBackgroundImage(UIImage(systemName: "mic.circle.fill"), for: .normal)
        } else {
            startRecording()
            hideResult()
            microphoneButton.setBackgroundImage(UIImage(systemName: "stop.circle.fill"), for: .normal)
        }
    }

    @IBAction func sourceTapped(_ sender: AnyObject) {
        // Open browser with sourceURL
        if let url = URL(string: sourceURL) {
            UIApplication.shared.open(url)
        }
    }
    
    func speakText(message: String ) {
        let speakMessage = message.components(separatedBy: ".")[0]
        do {
            try AVAudioSession.sharedInstance().setCategory(AVAudioSession.Category.playAndRecord, mode: .default, options: .defaultToSpeaker)
            try AVAudioSession.sharedInstance().setActive(true, options: .notifyOthersOnDeactivation)
        } catch {
            print("audioSession properties weren't set because of an error.")
        }

        let utterance = AVSpeechUtterance(string: speakMessage)
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")

        let synth = AVSpeechSynthesizer()
        synth.speak(utterance)

        defer {
            disableAVSession()
        }
    }

    private func disableAVSession() {
        do {
            try AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        } catch {
            print("audioSession properties weren't disable.")
        }
    }

    func showResult(type: String, title: String, message: String, veracity: Bool, source: String) {
        if (type != "not_found") {
            self.descriptionLabel.isHidden = false
            self.titleLabel.isHidden = false
            self.veracityLabel.isHidden = false

            self.titleLabel.text = title
            self.descriptionLabel.text = message
            self.speakText(message: message)
            self.veracityLabel.text = veracity ? "True" : "False"
            self.veracityLabel.backgroundColor = veracity ? UIColor.systemGreen : UIColor.systemRed
            if (source != "") {
                self.sourceButton.isHidden = false
                self.sourceURL = source
            }
        } else {
            self.descriptionLabel.isHidden = true
            self.titleLabel.isHidden = true
            self.veracityLabel.isHidden = false
            self.sourceButton.isHidden = true
            self.veracityLabel.text = "Not found"
            self.veracityLabel.backgroundColor = UIColor.darkGray
        }
    }

    func hideResult() {
        // Hide the result
        self.descriptionLabel.isHidden = true
        self.titleLabel.isHidden = true
        self.veracityLabel.isHidden = true
        self.sourceButton.isHidden = true
        self.textView.text = "Say the fact you want to check"
    }

    func checkVeracity(text: String) {
        // Show loading view
        let loadingView = UIView(frame: CGRect(x: 0, y: 0, width: self.view.frame.width, height: self.view.frame.height))
        loadingView.backgroundColor = UIColor.black.withAlphaComponent(0.5)
        let activityIndicator = UIActivityIndicatorView(style: .large)
        activityIndicator.center = loadingView.center
        activityIndicator.startAnimating()
        loadingView.addSubview(activityIndicator)
        self.view.addSubview(loadingView)

        let url = URL(string: "https://factchecker.futur.technology/fact_check?text=\(text.addingPercentEncoding(withAllowedCharacters: .urlHostAllowed) ?? "")")!
        let task = URLSession.shared.dataTask(with: url) { data, response, error in
            // Hide view
            DispatchQueue.main.async {
                loadingView.removeFromSuperview()
            }
            if let data = data,
                let response = response as? HTTPURLResponse,
                response.statusCode == 200 {
                if let json = try? JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] {
                    let type = json["type"] as? String
                    let veracity = json["check"] as? Bool
                    let message = json["message"] as? String
                    let title = json["title"] as? String
                    let source = json["source"] as? String

                    DispatchQueue.main.async {
                        self.showResult(
                            type: type ?? "not_found",
                            title: title ?? "",
                            message: message ?? "",
                            veracity: veracity ?? false,
                            source: source ?? ""
                        )
                    }
                }
            } else {
                // Log response error
                print("response: \(String(describing: response))")
                // Show error alert
                DispatchQueue.main.async {
                    self.hideResult()
                    let alert = UIAlertController(title: "Error", message: "An error occurred while checking the fact", preferredStyle: .alert)
                    alert.addAction(UIAlertAction(title: "OK", style: .default, handler: nil))
                    self.present(alert, animated: true)
                }
            }
        }
        task.resume()

    }

    func startRecording() {

        if recognitionTask != nil {
            recognitionTask?.cancel()
            recognitionTask = nil
        }

        let audioSession = AVAudioSession.sharedInstance()
        do {
            try audioSession.setCategory(.record, mode: .measurement, options: .duckOthers)
            try audioSession.setActive(true, options: .notifyOthersOnDeactivation)
        } catch {
            print("audioSession properties weren't set because of an error.")
        }

        recognitionRequest = SFSpeechAudioBufferRecognitionRequest()

        guard let inputNode: AVAudioInputNode = audioEngine.inputNode else {
            fatalError("Audio engine has no input node")
        }

        guard let recognitionRequest = recognitionRequest else {
            fatalError("Unable to create an SFSpeechAudioBufferRecognitionRequest object")
        }

        recognitionRequest.shouldReportPartialResults = true

        recognitionTask = speechRecognizer.recognitionTask(with: recognitionRequest) { result, error in
            var isFinal = false

            if let result = result {
                self.textView.text = result.bestTranscription.formattedString
                isFinal = result.isFinal
            }

            if (isFinal) {
                self.checkVeracity(text: self.textView.text)
            }

            if error != nil || isFinal {
                self.audioEngine.stop()
                inputNode.removeTap(onBus: 0)

                self.recognitionRequest = nil
                self.recognitionTask = nil

                //self.microphoneButton.isEnabled = true
            }
        }
        //inputNode.removeTap(onBus: 0)
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { (buffer: AVAudioPCMBuffer, when: AVAudioTime) in
            self.recognitionRequest?.append(buffer)
        }

        audioEngine.prepare()

        do {
            try audioEngine.start()
        } catch {
            print("audioEngine couldn't start because of an error.")
        }
    }

    func speechRecognizer(_ speechRecognizer: SFSpeechRecognizer, availabilityDidChange available: Bool) {
        if available {
            microphoneButton.isEnabled = true
        } else {
            microphoneButton.isEnabled = false
        }
    }
}
