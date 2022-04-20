const mongoose = require('mongoose');

const linkSchema = new mongoose.Schema({
  url: {
    type: String,
    required: true,
    unique: true,
  },
  source: {
    type: String,
    required: true,
  },
  graph: {
    type: String,
  },
  data: {
    type: Object,
  },
  processed: {
    type: Boolean,
    default: false,
  },
  error: {
    type: Boolean,
    default: false,
  },
});


linkSchema.index({ url: 1 }, { unique: true });

const factSchema = new mongoose.Schema({
  url: {
    type: String,
    required: true,
    unique: true,
  },
  data: {
    type: Object,
  },
  graph: {
    type: String,
  },
  source: {
    type: String,
    required: true,
  },
  createdAt: {
    type: Date,
    default: Date.now,
  },
});

factSchema.index({ url: 1 }, { unique: true });

module.exports = {
    Link: mongoose.model('Link', linkSchema),
    Fact: mongoose.model('Fact', factSchema),
}
