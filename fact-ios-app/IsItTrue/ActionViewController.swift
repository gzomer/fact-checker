//
//  ActionViewController.swift
//  IsItTrue
//
//  Created by Gustavo Zomer on 04/04/2022.
//  Copyright © 2022 Gustavo Zomer. All rights reserved.
//

import UIKit
import MobileCoreServices

class ActionViewController: UIViewController {

    @IBOutlet weak var titleLabel: UILabel!
    @IBOutlet weak var descriptionLabel: UILabel!
    @IBOutlet weak var veracityLabel: UILabel!
    @IBOutlet weak var sourceButton: UIButton!
    private var sourceURL: String!

    override func viewDidLoad() {
        super.viewDidLoad()
        hideResult()
        getExtensionContext()
    }

    func getExtensionContext() {
        for item in self.extensionContext!.inputItems as! [NSExtensionItem] {
            for provider in item.attachments! {
                if provider.hasItemConformingToTypeIdentifier(kUTTypeText as String) {
                    provider.loadItem(forTypeIdentifier: kUTTypeText as String, options: nil, completionHandler: { (text, error) in
                        OperationQueue.main.addOperation {
                            if let text = text as? String {
                                self.checkVeracity(url: "", text: text)
                            }
                        }
                    })
                }
                // Check url
                if provider.hasItemConformingToTypeIdentifier(kUTTypeURL as String) {
                    provider.loadItem(forTypeIdentifier: kUTTypeURL as String, options: nil, completionHandler: { (data, error) in
                        OperationQueue.main.addOperation {
                            let url = data as! NSURL
                            self.checkVeracity(url: url.absoluteString ?? "", text: "")
                        }
                    })
                }
            }
        }
    }


    func hideResult() {
        // Hide the result
        self.descriptionLabel.isHidden = true
        self.titleLabel.isHidden = true
        self.veracityLabel.isHidden = true
        self.sourceButton.isHidden = true
    }

    @IBAction func sourceTapped(_ sender: AnyObject) {
        // Open browser with sourceURL
        if let url = URL(string: sourceURL) {
            UIApplication.shared.open(url)
        }
    }

    func showResult(type: String, title: String, message: String, veracity: Bool, source: String) {
        if (type != "not_found") {
            self.descriptionLabel.isHidden = false
            self.titleLabel.isHidden = false
            self.veracityLabel.isHidden = false

            self.titleLabel.text = title
            self.descriptionLabel.text = message
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

    func checkVeracity(url: String, text: String) {
        // Show loading view
        let loadingView = UIView(frame: CGRect(x: 0, y: 0, width: self.view.frame.width, height: self.view.frame.height))
        loadingView.backgroundColor = UIColor.black.withAlphaComponent(0.5)
        let activityIndicator = UIActivityIndicatorView(style: .large)
        activityIndicator.center = loadingView.center
        activityIndicator.startAnimating()
        loadingView.addSubview(activityIndicator)
        self.view.addSubview(loadingView)

        var urlString = ""
        if (url != "") {
            urlString = "https://factchecker.futur.technology/fact_check?url=\(url.addingPercentEncoding(withAllowedCharacters: .urlHostAllowed) ?? "")"
        } else {
            urlString = "https://factchecker.futur.technology/fact_check?text=\(text.addingPercentEncoding(withAllowedCharacters: .urlHostAllowed) ?? "")"
        }

        let url = URL(string: urlString)!
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

    @IBAction func done() {
        // Return any edited content to the host app.
        // This template doesn't do anything, so we just echo the passed in items.
        self.extensionContext!.completeRequest(returningItems: self.extensionContext!.inputItems, completionHandler: nil)
    }

}
